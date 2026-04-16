/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_IMPL_H
#define INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_IMPL_H

#include <gnuradio/wisun/gated_power_squelch_relative_cc.h>

namespace gr {
namespace wisun {

class gated_power_squelch_relative_cc_impl : public gated_power_squelch_relative_cc
{
private:
    // Nothing to declare in this block.

public:
    gated_power_squelch_relative_cc_impl(const double relative_threshold,
                                         const double alpha,
                                         const int trailing_samples);
    ~gated_power_squelch_relative_cc_impl();

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
