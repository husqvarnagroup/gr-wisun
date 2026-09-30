/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "power_squelch_relative_cc_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

using input_type = gr_complex;
using output_type = gr_complex;

power_squelch_relative_cc::sptr
power_squelch_relative_cc::make(const double relative_threshold, const double alpha)
{
    return gnuradio::make_block_sptr<power_squelch_relative_cc_impl>(relative_threshold,
                                                                     alpha);
}


/*
 * The private constructor
 */
power_squelch_relative_cc_impl::power_squelch_relative_cc_impl(
    const double relative_threshold, const double alpha)
    : gr::sync_block("power_squelch_relative_cc",
                     gr::io_signature::make(1, 1, sizeof(input_type)),
                     gr::io_signature::make(1, 1, sizeof(output_type))),
      d_tracker(alpha, relative_threshold),
      d_output_active(false),
      d_channel(-1)
{
}

/*
 * Our virtual destructor.
 */
power_squelch_relative_cc_impl::~power_squelch_relative_cc_impl() {}

int power_squelch_relative_cc_impl::work(int noutput_items,
                                         gr_vector_const_void_star& input_items,
                                         gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);
    bool noise_floor_pwr_updated = false;

    for (int i = 0; i < noutput_items; i++) {
        noise_floor_pwr_updated |=
            d_tracker.update(in[i].real() * in[i].real() + in[i].imag() * in[i].imag());

        if (d_output_active) {
            out[i] = in[i];

            if (!d_tracker.above_threshold()) {
                d_output_active = false;
                gr::block::add_item_tag(0,
                                        this->nitems_written(0) + i,
                                        pmt::string_to_symbol("squelch_eob"),
                                        pmt::from_double(d_tracker.power()));
            }
        } else {
            out[i] = 0;

            if (d_tracker.above_threshold()) {
                d_output_active = true;
                gr::block::add_item_tag(0,
                                        this->nitems_written(0) + i + 1,
                                        pmt::string_to_symbol("squelch_sob"),
                                        pmt::from_double(d_tracker.power()));
            }
        }
    }

    if (noise_floor_pwr_updated) {
        d_logger->debug(
            "noise floor power (channel {:d}): {:.1f} dB; absolute threshold: {:.1f} dB",
            d_channel,
            10 * std::log10(d_tracker.noise_floor()),
            10 * std::log10(d_tracker.threshold()));
    }

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
