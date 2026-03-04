/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Information about the PCAP header is available at:
 * - https://datatracker.ietf.org/doc/draft-ietf-opsawg-pcap/
 * - https://wiki.wireshark.org/Development/LibpcapFileFormat#Record_.28Packet.29_Header
 *
 * Note: The PCAP format specifies that all file and packet record header fields are
 * always written in the characteristics of the machine writing the file. This means we do
 * not need to worry about endianness (the magic number is used to handle endianness when
 * reading the file).
 */

#include "pdu_add_pcap_header_impl.h"
#include <gnuradio/pdu.h>
#include <gnuradio/io_signature.h>

#define WTAP_ENCAP_IEEE802_15_4_NOFCS (230)

namespace gr {
namespace wisun {

static size_t pcap_file_header_length = sizeof(struct pcap_file_header);

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
    size_t input_length, payload_length;
    struct timespec curtime;
    struct pcap_packet_record_header packet_hdr;

    if (!pmt::is_pair(msg))
        throw std::runtime_error("received a malformed PDU message");

    /* if enabled, create PDU with global PCAP header initially */
    if (d_prepend_global_pcap_header && !d_global_pcap_header_done) {
        struct pcap_file_header fhdr;

        pmt::pmt_t global_header_vect = pmt::make_u8vector(pcap_file_header_length, 0);
        uint8_t* buf = pmt::u8vector_writable_elements(global_header_vect,
                                                       pcap_file_header_length);

        /* add global PCAP header */
        fhdr.magic_number  = 0xA1B2C3D4; /* indicates using seconds & microseconds */
        fhdr.major_version = 2;
        fhdr.minor_version = 0;
        fhdr.reserved1     = 0;
        fhdr.reserved2     = 0;
        fhdr.snap_len      = 0x7ff;
        fhdr.link_type     = WTAP_ENCAP_IEEE802_15_4_NOFCS;

        memcpy(buf, &fhdr, sizeof(fhdr));

        pmt::pmt_t global_hdr_msg = pmt::cons(pmt::get_PMT_NIL(), global_header_vect);
        message_port_pub(msgport_names::pdus(), global_hdr_msg);

        d_global_pcap_header_done = true;
    }

    msg_meta = pmt::car(msg);
    pmt::print(msg_meta);
    msg_vect = pmt::cdr(msg);
    input_length = pmt::blob_length(msg_vect);
    payload_length = input_length - 4;  /* first 4 bytes (SFD & PHR) are not part of the payload */
    const std::vector<uint8_t> in = pmt::u8vector_elements(msg_vect);

    /* create output PDU */
    size_t output_length = sizeof(struct pcap_packet_record_header) + payload_length;
    pmt::pmt_t out_vect = pmt::make_u8vector(output_length, 0);
    uint8_t* out = pmt::u8vector_writable_elements(out_vect, output_length);

    /* add PCAP packet record header */
    clock_gettime(CLOCK_REALTIME, &curtime);

    packet_hdr.timestamp_s            = curtime.tv_sec;
    packet_hdr.timestamp_us           = curtime.tv_nsec / 1000;
    packet_hdr.captured_packet_length = payload_length;
    packet_hdr.original_packet_length = payload_length;

    memcpy(out, &packet_hdr, sizeof(packet_hdr));

    /*
     * add data
     *
     * note: we skip the first 4 bytes (SFD & PHR)
     */
    for (size_t i = 0; i < payload_length; i++) {
        out[sizeof(struct pcap_packet_record_header) + i] = in[i + 4];
    }

    /* create & send msg */
    pmt::pmt_t out_msg = pmt::cons(pmt::get_PMT_NIL(), out_vect);
    message_port_pub(msgport_names::pdus(), out_msg);
}

} /* namespace wisun */
} /* namespace gr */
