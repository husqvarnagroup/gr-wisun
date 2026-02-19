/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "tag_based_dc_correction_ff_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

using input_type = float;
using output_type = float;

tag_based_dc_correction_ff::sptr
tag_based_dc_correction_ff::make(const std::string signal_start_tag,
                                 const std::string signal_end_tag,
                                 const int estimation_length)
{
    return gnuradio::make_block_sptr<tag_based_dc_correction_ff_impl>(
        signal_start_tag, signal_end_tag, estimation_length);
}


/*
 * The private constructor
 */
tag_based_dc_correction_ff_impl::tag_based_dc_correction_ff_impl(
    const std::string signal_start_tag,
    const std::string signal_end_tag,
    const int estimation_length)
    : gr::sync_block("tag_based_dc_correction_ff",
                     gr::io_signature::make(1, 1, sizeof(input_type)),
                     gr::io_signature::make(1, 1, sizeof(output_type))),
      d_state(state_no_signal),
      d_offset(0),
      d_signal_start_tag(signal_start_tag),
      d_signal_end_tag(signal_end_tag),
      d_estimation_length(estimation_length),
      d_estimation_sample_count(0)
{
}

/*
 * Our virtual destructor.
 */
tag_based_dc_correction_ff_impl::~tag_based_dc_correction_ff_impl() {}

int tag_based_dc_correction_ff_impl::work(int noutput_items,
                                          gr_vector_const_void_star& input_items,
                                          gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);
    std::vector<tag_t> tags;

    if (d_state == state_no_signal) { /* look for signal start tags */
        get_tags_in_range(tags,
                          0,
                          nitems_read(0),
                          nitems_read(0) + noutput_items,
                          pmt::string_to_symbol(d_signal_start_tag));

        /* handle samples */
        if (tags.size() == 0) { /* no signal start - just copy signal unmodified */
            memcpy(out, in, noutput_items * sizeof(float));
            return noutput_items;
        } else { /* found signal start - copy up to signal and switch to estimating state
                  */
            int samples_to_process = tags[0].offset - nitems_read(0);
            memcpy(out, in, samples_to_process * sizeof(float));
            d_offset = 0;
            d_estimation_sample_count = 0;
            d_state = state_estimating;
            return samples_to_process;
        }
    } else { /* handle samples until signal is lost */
        int usable_samples = noutput_items;
        bool signal_lost = false;

        /* look for signal lost tags */
        get_tags_in_range(tags,
                          0,
                          nitems_read(0),
                          nitems_read(0) + noutput_items,
                          pmt::string_to_symbol(d_signal_end_tag));
        if (tags.size() > 0) {
            usable_samples = tags[0].offset - nitems_read(0);
            signal_lost = true;
            if (usable_samples == 0) {
                /* signal lost right at start → switch to looking for signal */
                d_state = state_no_signal;
                return 1; /* consume 1 sample to avoid loop if we get both a signal start
                           * and end tag on the same sample */
            }
        }

        /* handle usable samples */
        if (d_state == state_estimating) { /* estimate from usable samples */
            if (signal_lost &&
                usable_samples <= d_estimation_length - d_estimation_sample_count) {
                /* not enough samples to get into correction phase */
                memcpy(out, in, usable_samples * sizeof(float));
                d_state = state_no_signal;
                return usable_samples;
            }

            for (int i = 0; i < usable_samples; i++) {
                /* process samples for estimation */
                d_offset += in[i];
                d_estimation_sample_count++;

                /* pass samples through unmodified */
                out[i] = in[i];

                /* check if estimation completed */
                if (d_estimation_sample_count == d_estimation_length) {
                    d_offset /= d_estimation_length;
                    d_state = state_correcting;
                    gr::block::add_item_tag(
                        0,
                        this->nitems_written(0) + i + 1,
                        pmt::string_to_symbol("dc_correction_correction_start"),
                        pmt::from_float(d_offset));
                    return i + 1;
                }
            }
        } else { /* correction phase */
            assert(d_state == state_correcting);
            for (int i = 0; i < usable_samples; i++) {
                out[i] = in[i] - d_offset;
            }
        }

        if (signal_lost) {
            d_state = state_no_signal;
        }
        return usable_samples;
    }
}

} /* namespace wisun */
} /* namespace gr */
