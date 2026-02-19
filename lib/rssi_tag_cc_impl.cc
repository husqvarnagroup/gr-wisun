/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "rssi_tag_cc_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

#pragma message("set the following appropriately and remove this warning")
using input_type = float;
#pragma message("set the following appropriately and remove this warning")
using output_type = float;
rssi_tag_cc::sptr rssi_tag_cc::make(const uint32_t n_samples)
{
    return gnuradio::make_block_sptr<rssi_tag_cc_impl>(n_samples);
}


/*
 * The private constructor
 */
rssi_tag_cc_impl::rssi_tag_cc_impl(const uint32_t n_samples)
    : gr::sync_block("rssi_tag_cc",
                     gr::io_signature::make(
                         1 /* min inputs */, 1 /* max inputs */, sizeof(input_type)),
                     gr::io_signature::make(
                         1 /* min outputs */, 1 /*max outputs */, sizeof(output_type)))
{
}

/*
 * Our virtual destructor.
 */
rssi_tag_cc_impl::~rssi_tag_cc_impl() {}

int rssi_tag_cc_impl::work(int noutput_items,
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
