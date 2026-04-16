/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_IMPL_H
#define INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_IMPL_H

#include <gnuradio/wisun/gated_power_squelch_relative_cc.h>
#include <gnuradio/filter/single_pole_iir.h>

namespace gr {
namespace wisun {

class gated_power_squelch_relative_cc_impl : public gated_power_squelch_relative_cc
{
private:
    double d_relative_threshold;
    double d_absolute_threshold;
    double d_pwr;
    double d_noise_floor_pwr;
    filter::single_pole_iir<double, double, double> d_iir;
    bool d_output_active;
    int d_delay;
    int d_trailing_samples;
    int d_trailing_samples_left;

public:
    gated_power_squelch_relative_cc_impl(const double relative_threshold,
                                         const double alpha,
                                         const int trailing_samples);
    ~gated_power_squelch_relative_cc_impl();

    double relative_threshold() const { return 10 * log10(d_relative_threshold); }
    void set_relative_threshold(double db);

    // Where all the action really happens
    void forecast(int noutput_items, gr_vector_int& ninput_items_required);

    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_IMPL_H */
