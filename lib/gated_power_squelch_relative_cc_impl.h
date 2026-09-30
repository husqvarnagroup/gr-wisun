/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_IMPL_H
#define INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_IMPL_H

#include "noise_floor_tracker.h"
#include <gnuradio/wisun/gated_power_squelch_relative_cc.h>

namespace gr {
namespace wisun {

class gated_power_squelch_relative_cc_impl : public gated_power_squelch_relative_cc
{
private:
    noise_floor_tracker d_tracker;
    bool d_output_active;
    int d_trailing_samples;
    int d_trailing_samples_left;
    int16_t d_channel;

public:
    gated_power_squelch_relative_cc_impl(const double relative_threshold,
                                         const double alpha,
                                         const int trailing_samples);
    ~gated_power_squelch_relative_cc_impl();

    void set_channel(int16_t channel) override { d_channel = channel; }
    double relative_threshold() const { return d_tracker.relative_threshold_db(); }
    void set_relative_threshold(double db) { d_tracker.set_relative_threshold_db(db); }

    // Where all the action really happens
    void forecast(int noutput_items, gr_vector_int& ninput_items_required) override;

    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items) override;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_IMPL_H */
