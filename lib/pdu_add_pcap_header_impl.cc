/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Information about the PCAP header is available at:
 * - https://datatracker.ietf.org/doc/draft-ietf-opsawg-pcap/
 * - https://wiki.wireshark.org/Development/LibpcapFileFormat#Record_.28Packet.29_Header
 */

#include "pdu_add_pcap_header_impl.h"
#include <gnuradio/pdu.h>
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

static size_t pcap_global_header_length = 24;
static const size_t pcap_packet_record_header_length = 16;

pdu_add_pcap_header::sptr pdu_add_pcap_header::make(const bool prepend_global_pcap_header)
{
    return gnuradio::make_block_sptr<pdu_add_pcap_header_impl>(
        prepend_global_pcap_header);
}


/*
 * The private constructor
 */
pdu_add_pcap_header_impl::pdu_add_pcap_header_impl(const bool prepend_global_pcap_header)
    : gr::block("pdu_add_pcap_header",
                gr::io_signature::make(0, 0, 0),
                gr::io_signature::make(0, 0, 0)),
      d_prepend_global_pcap_header(prepend_global_pcap_header),
      d_global_pcap_header_done(false)
{
    message_port_register_out(msgport_names::pdus());
    message_port_register_in(msgport_names::pdus());
    set_msg_handler(msgport_names::pdus(),
                    [this](pmt::pmt_t msg) { this->handle_msg(msg); });
}

/*
 * Our virtual destructor.
 */
pdu_add_pcap_header_impl::~pdu_add_pcap_header_impl() {}

void pdu_add_pcap_header_impl::handle_msg(pmt::pmt_t msg)
{
    pmt::pmt_t msg_meta;
    pmt::pmt_t msg_vect;
    size_t input_length;
    struct timespec curtime;

    if (!pmt::is_pair(msg))
        throw std::runtime_error("received a malformed PDU message");

    /*
     * Note: The PCAP format specifies that all file and packet record header fields are
     * always written in the characteristics of the machine writing the file. This means
     * we do not need to worry about endianness (the magic number is used to handle
     * endianness when reading the file).
     */

    /* if enabled, create PDU with global PCAP header initially */
    if (d_prepend_global_pcap_header && !d_global_pcap_header_done) {
        pmt::pmt_t global_header_vect = pmt::make_u8vector(pcap_global_header_length, 0);
        uint8_t* buf = pmt::u8vector_writable_elements(global_header_vect,
                                                       pcap_global_header_length);

        /* add global PCAP header */

        /*
         *                         1                   2                   3
         *     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
         *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
         *  0 |                          Magic Number                         |
         *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
         *  4 |         Major Version         |         Minor Version         |
         *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
         *  8 |                           Reserved1                           |
         *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
         * 12 |                           Reserved2                           |
         *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
         * 16 |                            SnapLen                            |
         *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
         * 20 |               LinkType and additional information             |
         *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
         */

        *(uint32_t *)&buf[0] = (uint32_t)0xA1B2C3D4; /* magic number; use seconds & microseconds */
        *(uint16_t *)&buf[4] = (uint16_t)2; /* major version */
        *(uint16_t *)&buf[6] = (uint16_t)0; /* minor version */
        *(uint32_t *)&buf[8] = (uint32_t)0; /* reserved 1 */
        *(uint32_t *)&buf[12] = (uint32_t)0; /* reserved 2 */
        *(uint32_t *)&buf[16] = (uint32_t)0x7ff; /* snap len */
        *(uint16_t *)&buf[20] = (uint32_t)230; /* link type: 230 (WTAP_ENCAP_IEEE802_15_4_NOFCS) */
        pmt::pmt_t global_hdr_msg = pmt::cons(pmt::get_PMT_NIL(), global_header_vect);
        message_port_pub(msgport_names::pdus(), global_hdr_msg);

        d_global_pcap_header_done = true;
    }

    msg_meta = pmt::car(msg);
    pmt::print(msg_meta);
    msg_vect = pmt::cdr(msg);
    input_length = pmt::blob_length(msg_vect);
    const std::vector<uint8_t> in = pmt::u8vector_elements(msg_vect);

    /* create output PDU */
    size_t output_length = pcap_packet_record_header_length + input_length - 4;
    pmt::pmt_t out_vect = pmt::make_u8vector(output_length, 0);
    uint8_t* out = pmt::u8vector_writable_elements(out_vect, output_length);

    /* add PCAP packet record header */

    /*
     *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     *  0 |                      Timestamp (Seconds)                      |
     *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     *  4 |            Timestamp (Microseconds or nanoseconds)            |
     *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     *  8 |                    Captured Packet Length                     |
     *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     * 12 |                    Original Packet Length                     |
     *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     */

    clock_gettime(CLOCK_REALTIME, &curtime);
    *(uint32_t *)&out[0] = (uint32_t)(curtime.tv_sec);
    *(uint32_t *)&out[4] = (uint32_t)(curtime.tv_nsec / 1000);
    *(uint32_t *)&out[8] = (uint32_t)input_length - 4;
    *(uint32_t *)&out[12] = (uint32_t)input_length - 4;

    /*
     * add data
     *
     * note: we skip the first 4 bytes (SFD & PHR)
     */
    for (size_t i = 4; i < input_length; i++) {
        out[pcap_packet_record_header_length + i - 4] = in[i];
    }

    /* create & send msg */
    pmt::pmt_t out_msg = pmt::cons(pmt::get_PMT_NIL(), out_vect);
    message_port_pub(msgport_names::pdus(), out_msg);
}

} /* namespace wisun */
} /* namespace gr */
