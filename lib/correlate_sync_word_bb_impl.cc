/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "correlate_sync_word_bb_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

static const uint16_t correlation_preamble_bits = 24;
static const uint16_t sfd_bits = 16;
static const uint16_t phr_bits = 16;

using input_type = uint8_t;
using output_type = uint8_t;

correlate_sync_word_bb::sptr correlate_sync_word_bb::make(uint16_t sfd)
{
    return gnuradio::make_block_sptr<correlate_sync_word_bb_impl>(sfd);
}


/*
 * The private constructor
 */
correlate_sync_word_bb_impl::correlate_sync_word_bb_impl(uint16_t sfd)
    : gr::sync_block("correlate_sync_word_bb",
                     gr::io_signature::make(1, 1, sizeof(input_type)),
                     gr::io_signature::make(1, 1, sizeof(output_type))),
      d_sfd(sfd),
      d_preamble_bit_counter(0),
      d_preamble_last_bit(2),
      d_sfd_data(0),
      d_phr_data(0)
{
    set_history(sfd_bits + phr_bits + 1);
    declare_sample_delay(history() - 1);
}

/*
 * Our virtual destructor.
 */
correlate_sync_word_bb_impl::~correlate_sync_word_bb_impl() {}

int correlate_sync_word_bb_impl::work(int noutput_items,
                                      gr_vector_const_void_star& input_items,
                                      gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);

    // do signal processing
    for (int i = 0; i < noutput_items; i++) {
        /* preamble detection */
        if (in[i] != d_preamble_last_bit) {
            d_preamble_bit_counter++;
        } else {
            d_preamble_bit_counter = 1;
        }
        d_preamble_last_bit = in[i];

        /* store data of start-of-frame delimiter (SFD) */
        d_sfd_data = (d_sfd_data << 1) + in[i + sfd_bits];

        /* store data of PHY header (PHR) */
        d_phr_data = (d_phr_data << 1) + in[i + sfd_bits + phr_bits];

        /* check for start */
        if (d_preamble_bit_counter >= correlation_preamble_bits &&
            d_preamble_last_bit == 1 && d_sfd_data == d_sfd) {
            /* PHR bit 0: mode switch */
            uint8_t phr_mode_switch = d_phr_data >> 15;
            /* PHR bit 3: FCS type */
            uint8_t phr_fcs_type = (d_phr_data & 0x1000) >> 12;
            /* PHR bit 4: data_whitening */
            uint8_t phr_data_whitening = (d_phr_data & 0x0800) >> 11;
            /* PHR bits 5-15: frame length */
            uint16_t phr_frame_length = d_phr_data & 0x07ff;

            d_logger->notice("packed detected: {:d} bytes (preamble length: {:d} symbols)",
                             phr_frame_length, d_preamble_bit_counter);
            if (phr_frame_length == 0) {
                d_logger->warn("ignoring zero-length packet");
                break;
            }

            /* add the packet tag */
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1,
                                    pmt::string_to_symbol("wisun-packet"),
                                    pmt::from_long(phr_frame_length));

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
             */
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1,
                                    pmt::string_to_symbol("wisun-preamble-length"),
                                    pmt::from_long(d_preamble_bit_counter));
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1,
                                    pmt::string_to_symbol("wisun-packet-sfd"),
                                    pmt::from_long(d_sfd));
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1 + 16,
                                    pmt::string_to_symbol("wisun-packet-phr"),
                                    pmt::from_long(d_phr_data));
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1 + 16 + 0,
                                    pmt::string_to_symbol("wisun-packet-phr-mode-switch"),
                                    pmt::from_long(phr_mode_switch));
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1 + 16 + 3,
                                    pmt::string_to_symbol("wisun-packet-phr-fcs-type"),
                                    pmt::from_long(phr_fcs_type));
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1 + 16 + 4,
                                    pmt::string_to_symbol("wisun-packet-phr-data-whitening"),
                                    pmt::from_long(phr_data_whitening));
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1 + 16 + 5,
                                    pmt::string_to_symbol("wisun-packet-phr-frame-length"),
                                    pmt::from_long(phr_frame_length));
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1 + 32,
                                    pmt::string_to_symbol("wisun-packet-payload"),
                                    pmt::get_PMT_NIL());
            /* TODO verify this (is header included in frame length?) */
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i + 1 + 8 * phr_frame_length - 1,
                                    pmt::string_to_symbol("wisun-packet-end"),
                                    pmt::get_PMT_NIL());
        }

        out[i] = in[i];
    }

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
