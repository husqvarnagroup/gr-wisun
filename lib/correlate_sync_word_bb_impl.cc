/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "correlate_sync_word_bb_impl.h"
#include "fec.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

static const uint16_t correlation_preamble_bits = 24;
static const uint16_t sfd_bits = 16;
static const uint16_t phr_bits = 16;

/*
 * Number of bits the PHY header of a coded frame occupies on air: it is exactly the
 * first interleaver block, i.e. 16 code symbols for the 16 header bits.
 */
static const uint16_t coded_phr_bits = 2 * phr_bits;

using input_type = uint8_t;
using output_type = uint8_t;

correlate_sync_word_bb::sptr correlate_sync_word_bb::make(uint16_t sfd, bool fec)
{
    return gnuradio::make_block_sptr<correlate_sync_word_bb_impl>(sfd, fec);
}


/*
 * The private constructor
 */
correlate_sync_word_bb_impl::correlate_sync_word_bb_impl(uint16_t sfd, bool fec)
    : gr::sync_block("correlate_sync_word_bb",
                     gr::io_signature::make(1, 1, sizeof(input_type)),
                     gr::io_signature::make(1, 1, sizeof(output_type))),
      d_sfd(sfd),
      d_fec(fec),
      d_preamble_bit_counter(0),
      d_preamble_last_bit(2),
      d_sfd_data(0),
      d_phr_data(0),
      d_channel(-1)
{
    set_history(sfd_bits + (d_fec ? coded_phr_bits : phr_bits) + 1);
    declare_sample_delay(history() - 1);
}

/*
 * Our virtual destructor.
 */
correlate_sync_word_bb_impl::~correlate_sync_word_bb_impl() {}

uint16_t correlate_sync_word_bb_impl::decode_coded_phr(const uint8_t* code_bits,
                                                       unsigned& metric)
{
    uint8_t deinterleaved[coded_phr_bits];
    uint8_t decoded[phr_bits];

    fec::deinterleave(code_bits, deinterleaved, 1);
    metric = fec::viterbi_decode(deinterleaved, phr_bits, decoded);

    /* the PHY header is transmitted most significant bit first */
    uint16_t phr = 0;
    for (size_t bit = 0; bit < phr_bits; bit++) {
        phr = (uint16_t)((phr << 1) | decoded[bit]);
    }
    return phr;
}

int correlate_sync_word_bb_impl::work(int noutput_items,
                                      gr_vector_const_void_star& input_items,
                                      gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);
    const uint16_t on_air_phr_bits = d_fec ? coded_phr_bits : phr_bits;

    // do signal processing
    for (int i = 0; i < noutput_items; i++) {
        /* the data itself is passed through unmodified */
        out[i] = in[i];

        /* preamble detection */
        if (in[i] != d_preamble_last_bit) {
            d_preamble_bit_counter++;
        } else {
            d_preamble_bit_counter = 1;
        }
        d_preamble_last_bit = in[i];

        /* store data of start-of-frame delimiter (SFD) */
        d_sfd_data = (uint16_t)((d_sfd_data << 1) + in[i + sfd_bits]);

        /* store data of PHY header (PHR); twice as many bits if the frame is coded */
        d_phr_data = (d_phr_data << 1) + in[i + sfd_bits + on_air_phr_bits];

        /* check for start */
        if (d_preamble_bit_counter >= correlation_preamble_bits &&
            d_preamble_last_bit == 1 && d_sfd_data == d_sfd) {
            uint16_t phr;
            unsigned phr_metric = 0;
            if (d_fec) {
                /*
                 * The PHY header is inside the coded block, so it has to be decoded
                 * before anything else can be read. It is the first interleaver block
                 * and the one part of the frame that is not whitened, so this needs no
                 * PN9 state and can happen straight off the first 4 octets.
                 */
                uint8_t code_bits[coded_phr_bits];
                for (size_t bit = 0; bit < coded_phr_bits; bit++) {
                    code_bits[bit] = (d_phr_data >> (coded_phr_bits - 1 - bit)) & 1;
                }
                phr = decode_coded_phr(code_bits, phr_metric);
            } else {
                phr = (uint16_t)d_phr_data;
            }

            /* PHR bit 0: mode switch */
            uint8_t phr_mode_switch = phr >> 15;
            /* PHR bit 3: FCS type */
            uint8_t phr_fcs_type = (phr & 0x1000) >> 12;
            /* PHR bit 4: data_whitening */
            uint8_t phr_data_whitening = (phr & 0x0800) >> 11;
            /* PHR bits 5-15: frame length */
            uint16_t phr_frame_length = phr & 0x07ff;

            /*
             * Number of octets to collect from the first bit of the SFD onwards. For a
             * coded frame the frame length counts the frame before it was encoded, so
             * framing has to be driven by the on-air length instead.
             */
            uint32_t packet_octets =
                d_fec ? 2 + fec::coded_length(phr_frame_length) : phr_frame_length;

            if (d_fec) {
                d_logger->notice("packet detected (channel {:d}): {:d} bytes, "
                                 "{:d} bytes on air (preamble length: {:d} symbols, "
                                 "header path metric: {:d})",
                                 d_channel,
                                 phr_frame_length,
                                 packet_octets,
                                 d_preamble_bit_counter,
                                 phr_metric);
            } else {
                d_logger->notice("packet detected (channel {:d}): "
                                 "{:d} bytes (preamble length: {:d} symbols)",
                                 d_channel,
                                 phr_frame_length,
                                 d_preamble_bit_counter);
            }

            if (phr_frame_length == 0) {
                d_logger->warn("ignoring zero-length packet");
                continue;
            }

            /* add the packet tag */
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1,
                                    pmt::string_to_symbol("wisun-packet"),
                                    pmt::from_long(packet_octets));

            /* add tags for preamble, length, options & payload
             *
             * note: these are not functionally required, but can be
             * useful when looking at the plots. preamble length is required in automated
             * tests.
             *
             * note: the preamble length tag is added to the first symbol of the actual
             * packet (first bit of sync word) rather than to the last bit of the
             * preamble. this makes it available in the message containing the packet data
             * in the packet receivers (the preamble samples are cut away by the
             * packet_data_gate_bb block).
             *
             * note: for a coded frame the individual header fields have no position of
             * their own on air, so all header tags go to the start of the coded header.
             */
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1,
                                    pmt::string_to_symbol("wisun-preamble-length"),
                                    pmt::from_long(d_preamble_bit_counter));
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1,
                                    pmt::string_to_symbol("wisun-packet-sfd"),
                                    pmt::from_long(d_sfd));
            const uint64_t phr_tag_offset = this->nitems_written(0) + i + 1 + sfd_bits;
            gr::block::add_item_tag(0,
                                    phr_tag_offset,
                                    pmt::string_to_symbol("wisun-packet-phr"),
                                    pmt::from_long(phr));
            gr::block::add_item_tag(0,
                                    phr_tag_offset,
                                    pmt::string_to_symbol("wisun-packet-phr-mode-switch"),
                                    pmt::from_long(phr_mode_switch));
            gr::block::add_item_tag(0,
                                    phr_tag_offset + (d_fec ? 0 : 3),
                                    pmt::string_to_symbol("wisun-packet-phr-fcs-type"),
                                    pmt::from_long(phr_fcs_type));
            gr::block::add_item_tag(
                0,
                phr_tag_offset + (d_fec ? 0 : 4),
                pmt::string_to_symbol("wisun-packet-phr-data-whitening"),
                pmt::from_long(phr_data_whitening));
            gr::block::add_item_tag(
                0,
                phr_tag_offset + (d_fec ? 0 : 5),
                pmt::string_to_symbol("wisun-packet-phr-frame-length"),
                pmt::from_long(phr_frame_length));
            gr::block::add_item_tag(0,
                                    phr_tag_offset + on_air_phr_bits,
                                    pmt::string_to_symbol("wisun-packet-payload"),
                                    pmt::get_PMT_NIL());
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1 + 8 * packet_octets -
                                        1,
                                    pmt::string_to_symbol("wisun-packet-end"),
                                    pmt::get_PMT_NIL());
        }
    }

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
