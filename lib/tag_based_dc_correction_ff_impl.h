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
    // Nothing to declare in this block.

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
