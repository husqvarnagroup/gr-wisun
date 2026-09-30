/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "fec.h"
#include "pdu_fec_decode_impl.h"
#include <gnuradio/io_signature.h>
#include <gnuradio/pdu.h>
#include <pmt/pmt.h>
#include <cstring>

namespace gr {
namespace wisun {

/* number of octets of start-of-frame delimiter preceding the coded block */
static const size_t sfd_octets = 2;

/*
 * Maximum tolerated path metric, as a fraction of the number of code symbols.
 *
 * Against true code symbols the metric is near zero; against anything else it
 * settles around 0.25 per code symbol, because a random bit pair disagrees with the
 * best available branch about a quarter of the time. Anything above an eighth is
 * therefore not a damaged frame, it is not a frame.
 */
static const unsigned metric_limit_divisor = 8;

static const pmt::pmt_t pmt_key_phr = pmt::string_to_symbol("wisun-packet-phr");
static const pmt::pmt_t pmt_key_metric = pmt::string_to_symbol("wisun-fec-metric");
static const pmt::pmt_t pmt_key_fcs_valid = pmt::string_to_symbol("wisun-fcs-valid");

pdu_fec_decode::sptr pdu_fec_decode::make(bool drop_invalid_frames)
{
    return gnuradio::make_block_sptr<pdu_fec_decode_impl>(drop_invalid_frames);
}


/*
 * The private constructor
 */
pdu_fec_decode_impl::pdu_fec_decode_impl(bool drop_invalid_frames)
    : gr::block("pdu_fec_decode",
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
pdu_fec_decode_impl::~pdu_fec_decode_impl() {}

void pdu_fec_decode_impl::handle_msg(pmt::pmt_t msg)
{
    if (!pmt::is_pair(msg)) {
        throw std::runtime_error("received a malformed PDU message");
    }

    pmt::pmt_t msg_meta = pmt::car(msg);
    pmt::pmt_t msg_vect = pmt::cdr(msg);
    const size_t input_length = pmt::blob_length(msg_vect);

    if (input_length <= sfd_octets) {
        d_logger->warn("dropping short PDU ({:d} octets)", input_length);
        return;
    }

    const std::vector<uint8_t> in = pmt::u8vector_elements(msg_vect);
    const size_t coded_octets = input_length - sfd_octets;

    /*
     * The interleaver works on blocks of 4 octets and the PHY header is exactly the
     * first block, so anything that is not a whole number of blocks cannot be a
     * coded frame.
     */
    if (coded_octets % (fec::interleaver_block_bits / 8) != 0) {
        d_logger->warn("dropping PDU with {:d} coded octets "
                       "(not a whole number of interleaver blocks)",
                       coded_octets);
        return;
    }

    /*
     * Unpack the code symbols, least significant bit of each octet first: that undoes
     * the packing done in the stream domain and restores transmission order.
     */
    std::vector<uint8_t> code_bits(8 * coded_octets);
    for (size_t i = 0; i < coded_octets; i++) {
        for (size_t bit = 0; bit < 8; bit++) {
            code_bits[8 * i + bit] = (in[sfd_octets + i] >> bit) & 1;
        }
    }

    const size_t n_blocks = code_bits.size() / fec::interleaver_block_bits;
    const size_t n_symbols = code_bits.size() / 2;
    std::vector<uint8_t> deinterleaved(code_bits.size());
    std::vector<uint8_t> info_bits(n_symbols);

    fec::deinterleave(code_bits.data(), deinterleaved.data(), n_blocks);
    const unsigned metric =
        fec::viterbi_decode(deinterleaved.data(), n_symbols, info_bits.data());

    if (metric > n_symbols / metric_limit_divisor) {
        d_logger->warn("dropping PDU: path metric {:d} over {:d} code symbols "
                       "is too high for this to be a frame",
                       metric,
                       n_symbols);
        return;
    }

    /* the PHY header is transmitted most significant bit first */
    uint16_t phr = 0;
    for (size_t bit = 0; bit < 8 * fec::phr_octets; bit++) {
        phr = (uint16_t)((phr << 1) | info_bits[bit]);
    }
    const uint16_t frame_length = phr & 0x07ff;
    const bool fcs16 = (phr & 0x1000) != 0;

    /* cross-check against the header the correlator decoded off the first block */
    if (pmt::dict_has_key(msg_meta, pmt_key_phr)) {
        const uint16_t expected =
            (uint16_t)pmt::to_long(pmt::cdr(pmt::assoc(pmt_key_phr, msg_meta)));
        if (expected != phr) {
            d_logger->warn("decoded PHY header 0x{:04x} disagrees with 0x{:04x} "
                           "from the sync word correlator",
                           phr,
                           expected);
        }
    }

    if (8 * fec::phr_octets + 8 * (size_t)frame_length > info_bits.size()) {
        d_logger->warn("dropping PDU: decoded frame length {:d} does not fit in "
                       "{:d} decoded octets",
                       frame_length,
                       info_bits.size() / 8);
        return;
    }

    /* everything but the PHY header is least significant bit first */
    std::vector<uint8_t> psdu(frame_length);
    for (size_t i = 0; i < frame_length; i++) {
        uint8_t octet = 0;
        for (size_t bit = 0; bit < 8; bit++) {
            octet |= (uint8_t)(info_bits[8 * fec::phr_octets + 8 * i + bit] << bit);
        }
        psdu[i] = octet;
    }
    /*
     * Note: the tail and padding bits following the PSDU are deliberately not
     * checked. They are zero tail bits followed by padding whose value has been seen
     * to be ones rather than zeros, so nothing may be concluded from them.
     */

    const bool fcs_valid = fec::fcs_valid(psdu.data(), psdu.size(), fcs16);
    if (!fcs_valid) {
        d_logger->warn("frame check sequence mismatch ({:d}-octet FCS, "
                       "frame length {:d}, path metric {:d}){:s}",
                       fec::fcs_octets(fcs16),
                       frame_length,
                       metric,
                       d_drop_invalid_frames ? "" : " - forwarding anyway");
        if (d_drop_invalid_frames) {
            return;
        }
    }

    /*
     * Emit the same layout the uncoded receive path produces: start-of-frame
     * delimiter, PHY header, then the PSDU without its frame check sequence.
     */
    const size_t fcs_len = fec::fcs_octets(fcs16);
    const size_t payload_length = psdu.size() > fcs_len ? psdu.size() - fcs_len : 0;
    /* not const: pmt wants a modifiable reference for the length */
    size_t output_length = sfd_octets + fec::phr_octets + payload_length;
    pmt::pmt_t out_vect = pmt::make_u8vector(output_length, 0);
    uint8_t* out = pmt::u8vector_writable_elements(out_vect, output_length);

    out[0] = in[0];
    out[1] = in[1];
    /* the decoded header goes out most significant octet first, as it reads */
    out[2] = (uint8_t)(phr >> 8);
    out[3] = (uint8_t)(phr & 0xff);
    memcpy(&out[sfd_octets + fec::phr_octets], psdu.data(), payload_length);

    pmt::pmt_t meta = pmt::dict_add(msg_meta, pmt_key_metric, pmt::from_long(metric));
    meta = pmt::dict_add(meta, pmt_key_fcs_valid, pmt::from_bool(fcs_valid));

    message_port_pub(msgport_names::pdus(), pmt::cons(meta, out_vect));
}

} /* namespace wisun */
} /* namespace gr */
