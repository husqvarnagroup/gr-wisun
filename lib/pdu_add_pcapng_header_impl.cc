/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Information about the PCAPNG file format is available at:
 * - https://www.ietf.org/archive/id/draft-tuexen-opsawg-pcapng-04.html
 * - https://pcapng.com/
 *
 * Information about the TAP link type can be found here:
 * - https://exegin.com/wp-content/uploads/ieee802154_tap.pdf
 */

#include "pdu_add_pcapng_header_impl.h"
#include <gnuradio/pdu.h>
#include <gnuradio/io_signature.h>
#include <pmt/pmt.h>

#define WTAP_ENCAP_IEEE802_15_4_NOFCS (230)
#define WTAP_ENCAP_IEEE802_15_4_TAP (283)

namespace gr {
namespace wisun {

static const std::string if_name = "GNU Radio Wi-SUN Sniffer";
static size_t if_name_padding = -if_name.length() % 4;
static size_t idb_options_length = 4 + if_name.length() + if_name_padding + 4;

static size_t shb_length = sizeof(struct pcapng_section_header_block_no_options);
static size_t idb_length = sizeof(struct pcapng_interface_description_block_base) + idb_options_length + 4;
static size_t epb_base_length = sizeof(struct pcapng_enhanced_packet_block_base); /* length of EPB header at beginning of EPB */
static size_t epb_header_full_length = epb_base_length + 4; /* full length of EPB including 'block total length' at end */

static size_t tap_dlt_header_length_offset = 4;  /* length specified in TAP DLT headers does not include first 4 bytes (2 byte type, 2 byte length) */

static const pmt::pmt_t pmt_key_rss = pmt::string_to_symbol("packet-rssi");
static const pmt::pmt_t pmt_key_bit_rate = pmt::string_to_symbol("packet-bit-rate");
static const pmt::pmt_t pmt_key_channel_number = pmt::string_to_symbol("packet-channel-number");
static const pmt::pmt_t pmt_key_channel_page = pmt::string_to_symbol("packet-channel-page");
static const pmt::pmt_t pmt_key_phy_band = pmt::string_to_symbol("packet-phy-band");
static const pmt::pmt_t pmt_key_phy_type = pmt::string_to_symbol("packet-phy-type");
static const pmt::pmt_t pmt_key_phy_mode = pmt::string_to_symbol("packet-phy-mode");

pdu_add_pcapng_header::sptr
pdu_add_pcapng_header::make(const bool prepend_section_header_block,
                            const bool prepend_interface_description_block,
                            const bool use_tap_dlt)
{
    return gnuradio::make_block_sptr<pdu_add_pcapng_header_impl>(
        prepend_section_header_block, prepend_interface_description_block, use_tap_dlt);
}


/*
 * The private constructor
 */
pdu_add_pcapng_header_impl::pdu_add_pcapng_header_impl(
    const bool prepend_section_header_block,
    const bool prepend_interface_description_block,
    const bool use_tap_dlt)
    : gr::block("pdu_add_pcapng_header",
                gr::io_signature::make(0, 0, sizeof(0)),
                gr::io_signature::make(0, 0, sizeof(0))),
      d_prepend_section_header_block(prepend_section_header_block),
      d_section_header_block_done(false),
      d_prepend_interface_description_block(prepend_interface_description_block),
      d_interface_description_block_done(false),
      d_use_tap_dlt(use_tap_dlt)
{
    message_port_register_out(msgport_names::pdus());
    message_port_register_in(msgport_names::pdus());
    set_msg_handler(msgport_names::pdus(),
                    [this](pmt::pmt_t msg) { this->handle_msg(msg); });
}

/*
 * Our virtual destructor.
 */
pdu_add_pcapng_header_impl::~pdu_add_pcapng_header_impl() {}

void pdu_add_pcapng_header_impl::handle_msg(pmt::pmt_t msg)
{
    pmt::pmt_t msg_meta;
    pmt::pmt_t msg_vect;
    size_t input_length, payload_length, padding;
    struct timespec curtime;
    uint64_t timestamp;

    if (!pmt::is_pair(msg))
        throw std::runtime_error("received a malformed PDU message");

    /*
     * Note: The PCAPNG file format specifies that each section uses the endianness of the
     * capturing machine. This means we do not need to worry about endianness (the
     * byte-order magic number is used to handle endianness when reading the file).
     */

    /* if enabled, create PDU with section header block (SHB) initially */
    if (d_prepend_section_header_block && !d_section_header_block_done) {
        pmt::pmt_t shb_vect = pmt::make_u8vector(shb_length, 0);
        uint8_t* buf = pmt::u8vector_writable_elements(shb_vect, shb_length);

        /* add section header block */
        struct pcapng_section_header_block_no_options shb;

        shb.block_type             = 0x0a0d0d0a;
        shb.block_total_length     = shb_length;
        shb.byte_order_magic       = 0x1a2b3c4d;
        shb.major_version          = 1;
        shb.minor_version          = 0;
        shb.section_length         = 0xffffffffffffffff;
        shb.block_total_length_dup = shb_length;

        memcpy(buf, &shb, sizeof(shb));

        pmt::pmt_t shb_msg = pmt::cons(pmt::get_PMT_NIL(), shb_vect);
        message_port_pub(msgport_names::pdus(), shb_msg);

        d_section_header_block_done = true;
    }

    /* if enabled, create PDU with interface description block (IDB) initially */
    if (d_prepend_interface_description_block && !d_interface_description_block_done) {
        pmt::pmt_t idb_vect = pmt::make_u8vector(idb_length, 0);
        uint8_t* buf = pmt::u8vector_writable_elements(idb_vect, idb_length);

        /* add interface description block */
        struct pcapng_interface_description_block_base idb_base;
        uint16_t dlt = d_use_tap_dlt ? WTAP_ENCAP_IEEE802_15_4_TAP : WTAP_ENCAP_IEEE802_15_4_NOFCS;

        idb_base.block_type         = 0x00000001;
        idb_base.block_total_length = idb_length;
        idb_base.link_type          = dlt;
        idb_base.reserved           = 0;
        idb_base.snap_length        = 0;
        memcpy(buf, &idb_base, sizeof(idb_base));

        /* options: interface name */
        *(uint16_t *)&buf[16] = (uint16_t)2; /* option code */
        *(uint16_t *)&buf[18] = (uint16_t)if_name.length(); /* option length */
        for (size_t i = 0; i < if_name.length(); i++) {
            buf[20 + i] = if_name[i];
        }
        for (size_t i = 0; i < if_name_padding; i++) {
            buf[20 + if_name.length() + i] = 0;
        }

        /* options: end of options */
        *(uint16_t *)&buf[16 + idb_options_length - 4] = 0; /* option code */
        *(uint16_t *)&buf[16 + idb_options_length - 2] = 0; /* option length */

        *(uint32_t *)&buf[16 + idb_options_length] = (uint32_t)idb_length; /* block total length */

        pmt::pmt_t idb_msg = pmt::cons(pmt::get_PMT_NIL(), idb_vect);
        message_port_pub(msgport_names::pdus(), idb_msg);

        d_section_header_block_done = true;
    }

    msg_meta = pmt::car(msg);
    // pmt::print(msg_meta);
    msg_vect = pmt::cdr(msg);
    input_length = pmt::blob_length(msg_vect);
    payload_length = input_length - 4; /* first 4 bytes (PHY header) are not part of payload */
    padding = -payload_length % 4;
    const std::vector<uint8_t> in = pmt::u8vector_elements(msg_vect);

    /* create output PDU */
    size_t tap_header_length = 0;
    if (d_use_tap_dlt) {
        tap_header_length = 4;

        /* adjust length for metadata */
        if (pmt::dict_has_key(msg_meta, pmt_key_rss)) {
            tap_header_length += sizeof(struct ieee802_15_4_tap_dlt_header_rss);
        }
        if (pmt::dict_has_key(msg_meta, pmt_key_bit_rate)) {
            tap_header_length += sizeof(struct ieee802_15_4_tap_dlt_header_bit_rate);
        }
        if (pmt::dict_has_key(msg_meta, pmt_key_channel_number)) {
            tap_header_length += sizeof(struct ieee802_15_4_tap_dlt_header_channel_assignment);
        }
        if (pmt::dict_has_key(msg_meta, pmt_key_phy_band)) {
            tap_header_length += sizeof(struct ieee802_15_4_tap_dlt_header_sun_phy_information);
        }
    }
    size_t output_length = epb_header_full_length + tap_header_length + payload_length + padding;
    pmt::pmt_t out_vect = pmt::make_u8vector(output_length, 0);
    uint8_t* out = pmt::u8vector_writable_elements(out_vect, output_length);

    /* add enhanced packet block (EPB) */
    struct pcapng_enhanced_packet_block_base epb_base;

    clock_gettime(CLOCK_REALTIME, &curtime);
    timestamp = curtime.tv_sec * 1000000 + curtime.tv_nsec / 1000;

    epb_base.block_type             = 0x6;
    epb_base.block_total_length     = output_length;
    epb_base.interface_id           = 0;
    epb_base.timestamp_high         = (timestamp >> 32);
    epb_base.timestamp_low          = (timestamp & 0xffffffff);
    epb_base.captured_packet_length = payload_length + tap_header_length;
    epb_base.original_packet_length = payload_length + tap_header_length;
    memcpy(out, &epb_base, sizeof(epb_base));

    *(uint32_t *)&out[output_length - 4] = (uint32_t)output_length; /* block total length */

    /* add TAP header (if TAP DLT enabled) */
    uint16_t idx = sizeof(epb_base);
    if (d_use_tap_dlt) {
        struct ieee802_15_4_tap_dlt_header tap_hdr;
        /*
         * Note: in contrast to the PCAPNG specification (which states that each section
         * uses the endianness of the capturing machine), the IEEE 802.15.4 TAP link type
         * specification by Exegin states that all data fields are encoded in
         * little-endian byte order. This needs we need to take care of endianness.
         */
        tap_hdr.version           = 0;
        tap_hdr.padding           = 0;
        tap_hdr.tap_header_length = htole16(tap_header_length);
        memcpy(&out[idx], &tap_hdr, sizeof(tap_hdr));
        idx += sizeof(tap_hdr);

        /* RSSI */
        if (pmt::dict_has_key(msg_meta, pmt_key_rss)) {
            struct ieee802_15_4_tap_dlt_header_rss rss_hdr;
            pmt::pmt_t rssi_tag;
            float rssi;

            rssi_tag = pmt::assoc(pmt_key_rss, msg_meta);
            rssi = pmt::to_float(pmt::cdr(rssi_tag)); /* TODO allow RSSI offset correction */
            d_logger->debug("packet RSSI: {:f} dBm", rssi);
            rss_hdr.type = htole16(IEEE802_15_4_TAP_DLT_TLV_TYPE_RSS);
            rss_hdr.length = htole16(sizeof(rss_hdr) - tap_dlt_header_length_offset);

            /*
             * Note: on a little-endian machine, we could just use
             *
             * rss_hdr.value = rssi;
             *
             * The following has not been tested, but should (possibly) work to convert
             * float to LE:
             */
            uint32_t rssi_hack;
            memcpy(&rssi_hack, &rssi, 4);
            rssi_hack = htole32(rssi_hack);
            memcpy(&rss_hdr.value, &rssi_hack, 4);

            memcpy(&out[idx], &rss_hdr, sizeof(rss_hdr));
            idx += sizeof(rss_hdr);
        }

        /* bit rate */
        if (pmt::dict_has_key(msg_meta, pmt_key_bit_rate)) {
            struct ieee802_15_4_tap_dlt_header_bit_rate bit_rate_hdr;

            pmt::pmt_t bit_rate_tag = pmt::assoc(pmt_key_bit_rate, msg_meta);
            uint32_t bit_rate = pmt::to_long(pmt::cdr(bit_rate_tag));

            bit_rate_hdr.type = htole16(IEEE802_15_4_TAP_DLT_TLV_TYPE_BIT_RATE);
            bit_rate_hdr.length = htole16(sizeof(bit_rate_hdr) - tap_dlt_header_length_offset);
            bit_rate_hdr.bit_rate = bit_rate;

            memcpy(&out[idx], &bit_rate_hdr, sizeof(bit_rate_hdr));
            idx += sizeof(bit_rate_hdr);
        }

        /* channel assignment */
        if (pmt::dict_has_key(msg_meta, pmt_key_channel_number)) {
            struct ieee802_15_4_tap_dlt_header_channel_assignment channel_hdr;

            pmt::pmt_t channel_number_tag = pmt::assoc(pmt_key_channel_number, msg_meta);
            uint16_t channel_number = pmt::to_long(pmt::cdr(channel_number_tag));
            uint8_t channel_page = 0;
            if (pmt::dict_has_key(msg_meta, pmt_key_channel_page)) {
                pmt::pmt_t channel_page_tag = pmt::assoc(pmt_key_channel_page, msg_meta);
                channel_page = pmt::to_long(pmt::cdr(channel_page_tag));
            }

            channel_hdr.type = htole16(IEEE802_15_4_TAP_DLT_TLV_TYPE_CHANNEL_ASSIGNMENT);
            channel_hdr.length = htole16(3); /* note: padding does not count towards length */
            channel_hdr.channel_number = channel_number;
            channel_hdr.channel_page = channel_page;
            channel_hdr.padding = 0;

            memcpy(&out[idx], &channel_hdr, sizeof(channel_hdr));
            idx += sizeof(channel_hdr);
        }

        /* SUN PHY information */
        if (pmt::dict_has_key(msg_meta, pmt_key_phy_band)) {
            struct ieee802_15_4_tap_dlt_header_sun_phy_information phy_hdr;

            pmt::pmt_t phy_band_tag = pmt::assoc(pmt_key_phy_band, msg_meta);
            uint8_t phy_band = pmt::to_long(pmt::cdr(phy_band_tag));
            uint8_t phy_type = 0;
            uint8_t phy_mode = 0;
            if (pmt::dict_has_key(msg_meta, pmt_key_phy_type)) {
                pmt::pmt_t phy_type_tag = pmt::assoc(pmt_key_phy_type, msg_meta);
                phy_type = pmt::to_long(pmt::cdr(phy_type_tag));
            }
            if (pmt::dict_has_key(msg_meta, pmt_key_phy_mode)) {
                pmt::pmt_t phy_mode_tag = pmt::assoc(pmt_key_phy_mode, msg_meta);
                phy_mode = pmt::to_long(pmt::cdr(phy_mode_tag));
            }

            phy_hdr.type = htole16(IEEE802_15_4_TAP_DLT_TLV_TYPE_SUN_PHY_INFORMATION);
            phy_hdr.length = htole16(3); /* note: padding does not count towards length */
            phy_hdr.phy_band = phy_band;
            phy_hdr.phy_type = phy_type;
            phy_hdr.phy_mode = phy_mode;
            phy_hdr.padding = 0;

            memcpy(&out[idx], &phy_hdr, sizeof(phy_hdr));
            idx += sizeof(phy_hdr);
        }
    }

    assert(idx == epb_base_length + tap_header_length);

    /*
     * add data
     *
     * note: we skip the first 4 bytes (SFD & PHR)
     */
    for (size_t i = 0; i < payload_length; i++) {
        out[epb_base_length + tap_header_length + i] = in[i + 4];
    }

    /* add padding */
    for (size_t i = 0; i < padding; i++) {
        out[epb_base_length + tap_header_length + payload_length + i] = 0;
    }

    /* create & send msg */
    pmt::pmt_t out_msg = pmt::cons(pmt::get_PMT_NIL(), out_vect);
    message_port_pub(msgport_names::pdus(), out_msg);
}

} /* namespace wisun */
} /* namespace gr */
