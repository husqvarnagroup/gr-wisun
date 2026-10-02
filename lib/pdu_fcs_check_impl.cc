/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "fec.h"
#include "pdu_fcs_check_impl.h"
#include <gnuradio/io_signature.h>
#include <gnuradio/pdu.h>
#include <pmt/pmt.h>
#include <cstring>

namespace gr {
namespace wisun {

/* number of octets of start-of-frame delimiter preceding the PHY header */
static const size_t sfd_octets = 2;

static const pmt::pmt_t pmt_key_fcs_valid = pmt::string_to_symbol("wisun-fcs-valid");

namespace {

/*
 * The PHY header arrives packed bit-reversed within each octet: the stream
 * domain packs every bit least-significant-bit-first, but the PHY header is
 * transmitted most-significant-bit first (see docs/sun-fsk-fec.md). Reversing
 * it here is the only way this block needs to read it, to get at the frame
 * check sequence type.
 */
uint8_t reverse_bits(uint8_t b)
{
    b = (uint8_t)(((b & 0xF0) >> 4) | ((b & 0x0F) << 4));
    b = (uint8_t)(((b & 0xCC) >> 2) | ((b & 0x33) << 2));
    b = (uint8_t)(((b & 0xAA) >> 1) | ((b & 0x55) << 1));
    return b;
}

} // namespace

pdu_fcs_check::sptr pdu_fcs_check::make(bool drop_invalid_frames)
{
    return gnuradio::make_block_sptr<pdu_fcs_check_impl>(drop_invalid_frames);
}


/*
 * The private constructor
 */
pdu_fcs_check_impl::pdu_fcs_check_impl(bool drop_invalid_frames)
    : gr::block("pdu_fcs_check",
                gr::io_signature::make(0, 0, 0),
                gr::io_signature::make(0, 0, 0)),
      d_drop_invalid_frames(drop_invalid_frames)
{
    message_port_register_out(msgport_names::pdus());
    message_port_register_in(msgport_names::pdus());
    set_msg_handler(msgport_names::pdus(),
                    [this](pmt::pmt_t msg) { this->handle_msg(msg); });
}

/*
 * Our virtual destructor.
 */
pdu_fcs_check_impl::~pdu_fcs_check_impl() {}

void pdu_fcs_check_impl::handle_msg(pmt::pmt_t msg)
{
    if (!pmt::is_pair(msg)) {
        throw std::runtime_error("received a malformed PDU message");
    }

    pmt::pmt_t msg_meta = pmt::car(msg);
    pmt::pmt_t msg_vect = pmt::cdr(msg);
    const size_t input_length = pmt::blob_length(msg_vect);
    const size_t header_octets = sfd_octets + fec::phr_octets;

    if (input_length < header_octets) {
        d_logger->warn("dropping short PDU ({:d} octets)", input_length);
        return;
    }

    const std::vector<uint8_t> in = pmt::u8vector_elements(msg_vect);

    /* the PHY header, most significant bit first, is the only thing this block
     * needs to read: the frame check sequence type */
    const uint16_t phr = (uint16_t)((reverse_bits(in[sfd_octets]) << 8) |
                                    reverse_bits(in[sfd_octets + 1]));
    const bool fcs16 = (phr & 0x1000) != 0;

    const uint8_t* psdu = in.data() + header_octets;
    const size_t psdu_len = input_length - header_octets;

    const bool valid = fec::fcs_valid(psdu, psdu_len, fcs16);
    if (!valid) {
        d_logger->warn("frame check sequence mismatch ({:d}-octet FCS, "
                       "{:d} PSDU octets){:s}",
                       fec::fcs_octets(fcs16),
                       psdu_len,
                       d_drop_invalid_frames ? "" : " - forwarding anyway");
        if (d_drop_invalid_frames) {
            return;
        }
    }

    /*
     * Emit the same layout the coded path's pdu_fec_decode produces: start-of-
     * frame delimiter, PHY header, then the PSDU without its frame check
     * sequence.
     */
    const size_t fcs_len = fec::fcs_octets(fcs16);
    const size_t payload_length = psdu_len > fcs_len ? psdu_len - fcs_len : 0;
    /* not const: pmt wants a modifiable reference for the length */
    size_t output_length = header_octets + payload_length;
    pmt::pmt_t out_vect = pmt::make_u8vector(output_length, 0);
    uint8_t* out = pmt::u8vector_writable_elements(out_vect, output_length);

    out[0] = in[0];
    out[1] = in[1];
    /* the PHY header goes out most significant octet first, as it reads, the
     * same convention pdu_fec_decode's output uses */
    out[2] = (uint8_t)(phr >> 8);
    out[3] = (uint8_t)(phr & 0xff);
    memcpy(&out[header_octets], psdu, payload_length);

    pmt::pmt_t meta = pmt::dict_add(msg_meta, pmt_key_fcs_valid, pmt::from_bool(valid));

    message_port_pub(msgport_names::pdus(), pmt::cons(meta, out_vect));
}

} /* namespace wisun */
} /* namespace gr */
