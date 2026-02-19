/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "rssi_tag_cc_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

using input_type = gr_complex;
using output_type = gr_complex;

rssi_tag_cc::sptr rssi_tag_cc::make(const uint32_t n_samples)
{
    return gnuradio::make_block_sptr<rssi_tag_cc_impl>(n_samples);
}

/*
 * The private constructor
 */
rssi_tag_cc_impl::rssi_tag_cc_impl(const uint32_t n_samples)
    : gr::sync_block("rssi_tag_cc",
                     gr::io_signature::make(1, 1, sizeof(input_type)),
                     gr::io_signature::make(1, 1, sizeof(output_type))),
      d_n_samples(n_samples),
      d_sample_index(0),
      d_rssi(0)
{
}

/*
 * Our virtual destructor.
 */
rssi_tag_cc_impl::~rssi_tag_cc_impl() {}

int rssi_tag_cc_impl::work(int noutput_items,
                           gr_vector_const_void_star& input_items,
                           gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);

    for (int i = 0; i < noutput_items; i++) {
        out[i] = in[i];
        double mag_sqrd = in[i].real() * in[i].real() + in[i].imag() * in[i].imag();
        d_rssi += mag_sqrd;
        d_sample_index++;

        if (d_sample_index == d_n_samples) {
            /* calculate value */
            d_rssi /= d_n_samples;            // calculate average magnitude squared
            d_rssi = 10 * std::log10(d_rssi); // convert to dBm

            /* add tag */
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + i,
                                    pmt::string_to_symbol("rssi"),
                                    pmt::from_double(d_rssi));

            /* start over */
            d_sample_index = 0;
            d_rssi = 0;
        }
    }

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
