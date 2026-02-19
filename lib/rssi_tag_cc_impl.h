/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_RSSI_TAG_CC_IMPL_H
#define INCLUDED_WISUN_RSSI_TAG_CC_IMPL_H

#include <gnuradio/wisun/rssi_tag_cc.h>

namespace gr {
namespace wisun {

class rssi_tag_cc_impl : public rssi_tag_cc
{
private:
    const uint32_t d_n_samples;
    uint32_t d_sample_index;
    double d_rssi;

public:
    rssi_tag_cc_impl(const uint32_t n_samples);
    ~rssi_tag_cc_impl();

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_RSSI_TAG_CC_IMPL_H */
