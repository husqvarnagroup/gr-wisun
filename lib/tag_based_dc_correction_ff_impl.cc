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

#pragma message("set the following appropriately and remove this warning")
using input_type = float;
#pragma message("set the following appropriately and remove this warning")
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
                     gr::io_signature::make(
                         1 /* min inputs */, 1 /* max inputs */, sizeof(input_type)),
                     gr::io_signature::make(
                         1 /* min outputs */, 1 /*max outputs */, sizeof(output_type)))
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

#pragma message("Implement the signal processing in your block and remove this warning")
    // Do <+signal processing+>

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
