/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_TAG_BASED_DC_CORRECTION_FF_IMPL_H
#define INCLUDED_WISUN_TAG_BASED_DC_CORRECTION_FF_IMPL_H

#include <gnuradio/wisun/tag_based_dc_correction_ff.h>

namespace gr {
namespace wisun {

class tag_based_dc_correction_ff_impl : public tag_based_dc_correction_ff
{
private:
    enum state {
        state_no_signal = 0,
        state_estimating = 1,
        state_correcting = 2,
    };
    enum state d_state;
    double d_offset;
    std::string d_signal_start_tag;
    std::string d_signal_end_tag;
    int d_estimation_length;
    int d_estimation_sample_count;

public:
    tag_based_dc_correction_ff_impl(const std::string signal_start_tag,
                                    const std::string signal_end_tag,
                                    const int estimation_length);
    ~tag_based_dc_correction_ff_impl();

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_TAG_BASED_DC_CORRECTION_FF_IMPL_H */
