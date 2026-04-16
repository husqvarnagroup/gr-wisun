/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "gated_power_squelch_relative_cc_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

using input_type = gr_complex;
using output_type = gr_complex;

gated_power_squelch_relative_cc::sptr gated_power_squelch_relative_cc::make(
    const double relative_threshold, const double alpha, const int trailing_samples)
{
    return gnuradio::make_block_sptr<gated_power_squelch_relative_cc_impl>(
        relative_threshold, alpha, trailing_samples);
}


/*
 * The private constructor
 */
gated_power_squelch_relative_cc_impl::gated_power_squelch_relative_cc_impl(
    const double relative_threshold, const double alpha, const int trailing_samples)
    : gr::block("gated_power_squelch_relative_cc",
                gr::io_signature::make(1, 1, sizeof(input_type)),
                gr::io_signature::make(1, 1, sizeof(output_type))),
      d_pwr(1),
      d_noise_floor_pwr(1),
      d_iir(alpha),
      d_output_active(false),
      d_delay(1 / alpha),
      d_trailing_samples(trailing_samples),
      d_trailing_samples_left(0),
      d_channel(-1)
{
    set_relative_threshold(relative_threshold);
}


/*
 * Our virtual destructor.
 */
gated_power_squelch_relative_cc_impl::~gated_power_squelch_relative_cc_impl() {}

void gated_power_squelch_relative_cc_impl::forecast(int noutput_items,
                                                    gr_vector_int& ninput_items_required)
{
    /* we produce a lot fewer samples than we get, but the actual ratio depends on the
     * number of packets received, so no way to predict */
    ninput_items_required[0] = noutput_items * 10;
}

void gated_power_squelch_relative_cc_impl::set_relative_threshold(double db)
{
    if (db <= 0)

        throw std::out_of_range("relative_threshold db must be > 0\n");

    d_relative_threshold = std::pow(10.0, db / 10);
    d_absolute_threshold = d_noise_floor_pwr * d_relative_threshold;
}

int gated_power_squelch_relative_cc_impl::general_work(
    int noutput_items,
    gr_vector_int& ninput_items,
    gr_vector_const_void_star& input_items,
    gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);
    bool noise_floor_pwr_updated = false;
    int noutput_items_created = 0;

    for (int i = 0; i < ninput_items[0]; i++) {
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

        if (d_output_active && d_pwr < d_absolute_threshold) {
            d_output_active = false;
            d_logger->debug("signal lost (channel {:d})", d_channel);
            d_trailing_samples_left = d_trailing_samples;
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + noutput_items_created - 1,
                                    pmt::string_to_symbol("squelch_eob"),
                                    pmt::from_double(d_pwr));
        } else if (!d_output_active && d_pwr >= d_absolute_threshold) {
            d_logger->debug("signal detected (channel {:d})", d_channel);
            d_output_active = true;
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + noutput_items_created,
                                    pmt::string_to_symbol("squelch_sob"),
                                    pmt::from_double(d_pwr));
        }

        if (d_output_active) {
            out[noutput_items_created++] = in[i];
        } else if (d_trailing_samples_left > 0) {
            out[noutput_items_created++] = 0;
            d_trailing_samples_left--;
        }
    }

    if (noise_floor_pwr_updated) {
        d_logger->debug(
            "noise floor power (channel {:d}): {:.1f} dB; absolute threshold: {:.1f} dB",
            d_channel,
            10 * std::log10(d_noise_floor_pwr),
            10 * std::log10(d_absolute_threshold));
    }

    d_logger->debug("channel {}: general_work(noutput_items: {}, ninput_items[0]: {}):\n"
                    "- noutput_items_created: {}\n"
                    "- d_output_active: {}\n"
                    "- d_noise_floor_pwr: {:.3e}\n"
                    "- d_absolute_threshold: {:.3e}\n"
                    "- d_pwr: {:.3e}",
                    d_channel,
                    noutput_items,
                    ninput_items[0],
                    noutput_items_created,
                    d_output_active,
                    d_noise_floor_pwr,
                    d_absolute_threshold,
                    d_pwr);

    /* tell runtime system how many input items we consumed */
    consume_each(ninput_items[0]);

    /* tell runtime system how many output items we produced. */
    return noutput_items_created;
}

} /* namespace wisun */
} /* namespace gr */
