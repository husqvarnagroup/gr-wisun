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
      d_pwr(1),
      d_noise_floor_pwr(1),
      d_iir(alpha),
      d_output_active(false),
      d_delay(1 / alpha)
{
    set_relative_threshold(relative_threshold);
}

/*
 * Our virtual destructor.
 */
power_squelch_relative_cc_impl::~power_squelch_relative_cc_impl() {}

void power_squelch_relative_cc_impl::set_relative_threshold(double db)
{
    if (db <= 0)
        throw std::out_of_range("relative_threshold db must be > 0\n");

    d_relative_threshold = std::pow(10.0, db / 10);
    d_absolute_threshold = d_noise_floor_pwr * d_relative_threshold;
}

int power_squelch_relative_cc_impl::work(int noutput_items,
                                         gr_vector_const_void_star& input_items,
                                         gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);
    bool noise_floor_pwr_updated = false;

    for (int i = 0; i < noutput_items; i++) {
        d_pwr = d_iir.filter(in[i].real() * in[i].real() + in[i].imag() * in[i].imag());
        if (d_delay) { /* wait until filter is stable before recording lowest power */
            d_delay--;
            if (d_delay == 0) {
                d_logger->debug("delay done; d_pwr is {:f}", d_pwr);
            }
        } else if (d_pwr < d_noise_floor_pwr) {
            d_noise_floor_pwr = d_pwr;
            d_absolute_threshold = d_noise_floor_pwr * d_relative_threshold;
            noise_floor_pwr_updated = true;
        }

        if (d_output_active) {
            out[i] = in[i];

            if (d_pwr < d_absolute_threshold) {
                d_output_active = false;
                gr::block::add_item_tag(0,
                                        this->nitems_written(0) + i,
                                        pmt::string_to_symbol("squelch_eob"),
                                        pmt::from_double(d_pwr));
            }
        } else {
            out[i] = 0;

            if (d_pwr >= d_absolute_threshold) {
                d_output_active = true;
                gr::block::add_item_tag(0,
                                        this->nitems_written(0) + i + 1,
                                        pmt::string_to_symbol("squelch_sob"),
                                        pmt::from_double(d_pwr));
            }
        }
    }

    if (noise_floor_pwr_updated) {
        d_logger->debug("noise floor power: {:.1f} dB; absolute threshold: {:.1f} dB",
                        10 * std::log10(d_noise_floor_pwr),
                        10 * std::log10(d_absolute_threshold));
    }

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
