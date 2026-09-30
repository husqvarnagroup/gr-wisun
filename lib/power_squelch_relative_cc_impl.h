/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_POWER_SQUELCH_RELATIVE_CC_IMPL_H
#define INCLUDED_WISUN_POWER_SQUELCH_RELATIVE_CC_IMPL_H

#include "noise_floor_tracker.h"
#include <gnuradio/wisun/power_squelch_relative_cc.h>

namespace gr {
namespace wisun {

class power_squelch_relative_cc_impl : public power_squelch_relative_cc
{
private:
    noise_floor_tracker d_tracker;
    bool d_output_active;
    int16_t d_channel;

public:
    power_squelch_relative_cc_impl(const double relative_threshold, const double alpha);
    ~power_squelch_relative_cc_impl();

    void set_channel(int16_t channel) override { d_channel = channel; }
    double relative_threshold() const { return d_tracker.relative_threshold_db(); }
    void set_relative_threshold(double db) { d_tracker.set_relative_threshold_db(db); }

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items) override;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_POWER_SQUELCH_RELATIVE_CC_IMPL_H */
