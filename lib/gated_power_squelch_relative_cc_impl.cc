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
      d_tracker(alpha, relative_threshold),
      d_output_active(false),
      d_trailing_samples(trailing_samples),
      d_trailing_samples_left(0),
      d_channel(-1)
{
}


/*
 * Our virtual destructor.
 */
gated_power_squelch_relative_cc_impl::~gated_power_squelch_relative_cc_impl() {}

void gated_power_squelch_relative_cc_impl::forecast(int noutput_items,
                                                    gr_vector_int& ninput_items_required)
{
    /*
     * We usually produce a lot fewer items than we get, and by how much depends on how
     * much of the input held a signal, so there is no ratio to predict. What is certain
     * is that an item is never produced out of nothing, so producing noutput_items needs
     * at least that many input items - and asking for any more than that is harmful:
     * forecast is a minimum the scheduler has to satisfy before it will run the block at
     * all, so demanding a multiple of it leaves the last few items of a stream
     * unprocessed.
     */
    ninput_items_required[0] = noutput_items;
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
    int ninput_items_consumed = 0;

    for (int i = 0; i < ninput_items[0]; i++) {
        /*
         * Stop once the output buffer is full. The scheduler hands over every input item
         * that is available and bounds only noutput_items; it never reduces ninput_items
         * to fit the output buffer. An open squelch passes nearly everything through, so
         * whenever the downstream is backed up while input has piled up - the normal
         * state of affairs in the multi-channel receiver - this loop used to write past
         * the end of the output buffer.
         *
         * The check has to come before the sample is touched: processing it advances the
         * power estimate and the squelch state, so a sample whose output does not fit
         * must not be processed at all, or it would be processed twice.
         */
        if (noutput_items_created == noutput_items) {
            break;
        }

        noise_floor_pwr_updated |=
            d_tracker.update(in[i].real() * in[i].real() + in[i].imag() * in[i].imag());

        if (d_output_active && !d_tracker.above_threshold()) {
            d_output_active = false;
            d_logger->debug("signal lost (channel {:d})", d_channel);
            d_trailing_samples_left = d_trailing_samples;
            /*
             * Tag the first item that is no longer signal, which is the first trailing
             * zero. Tagging the item before it named the last item that *was* signal,
             * which is both the opposite of what squelch_sob does and one item too early
             * for the consumer: tag_based_dc_correction_ff takes this offset as the end
             * of the usable range, so it used to stop correcting one sample before the
             * signal actually ended. It also put the tag one item behind the range the
             * call produced whenever a burst ended on the first input sample of a call,
             * which happens routinely because the block stays open across calls.
             */
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + noutput_items_created,
                                    pmt::string_to_symbol("squelch_eob"),
                                    pmt::from_double(d_tracker.power()));
        } else if (!d_output_active && d_tracker.above_threshold()) {
            d_logger->debug("signal detected (channel {:d})", d_channel);
            d_output_active = true;
            gr::block::add_item_tag(0,
                                    this->nitems_written(0) + noutput_items_created,
                                    pmt::string_to_symbol("squelch_sob"),
                                    pmt::from_double(d_tracker.power()));
        }

        if (d_output_active) {
            out[noutput_items_created++] = in[i];
        } else if (d_trailing_samples_left > 0) {
            out[noutput_items_created++] = 0;
            d_trailing_samples_left--;
        }

        ninput_items_consumed++;
    }

    if (noise_floor_pwr_updated) {
        d_logger->debug(
            "noise floor power (channel {:d}): {:.1f} dB; absolute threshold: {:.1f} dB",
            d_channel,
            10 * std::log10(d_tracker.noise_floor()),
            10 * std::log10(d_tracker.threshold()));
    }

    /* tell runtime system how many input items we consumed */
    consume_each(ninput_items_consumed);

    /* tell runtime system how many output items we produced. */
    return noutput_items_created;
}

} /* namespace wisun */
} /* namespace gr */
