/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "pdu_add_pcapng_header_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

#pragma message("set the following appropriately and remove this warning")
using input_type = float;
#pragma message("set the following appropriately and remove this warning")
using output_type = float;
pdu_add_pcapng_header::sptr
pdu_add_pcapng_header::make(const bool prepend_section_header_block,
                            const bool prepend_interface_description_block)
{
    return gnuradio::make_block_sptr<pdu_add_pcapng_header_impl>(
        prepend_section_header_block, prepend_interface_description_block);
}


/*
 * The private constructor
 */
pdu_add_pcapng_header_impl::pdu_add_pcapng_header_impl(
    const bool prepend_section_header_block,
    const bool prepend_interface_description_block)
    : gr::block("pdu_add_pcapng_header",
                gr::io_signature::make(
                    1 /* min inputs */, 1 /* max inputs */, sizeof(input_type)),
                gr::io_signature::make(
                    1 /* min outputs */, 1 /*max outputs */, sizeof(output_type)))
{
}

/*
 * Our virtual destructor.
 */
pdu_add_pcapng_header_impl::~pdu_add_pcapng_header_impl() {}

void pdu_add_pcapng_header_impl::forecast(int noutput_items,
                                          gr_vector_int& ninput_items_required)
{
#pragma message( \
    "implement a forecast that fills in how many items on each input you need to produce noutput_items and remove this warning")
    /* <+forecast+> e.g. ninput_items_required[0] = noutput_items */
}

int pdu_add_pcapng_header_impl::general_work(int noutput_items,
                                             gr_vector_int& ninput_items,
                                             gr_vector_const_void_star& input_items,
                                             gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);

#pragma message("Implement the signal processing in your block and remove this warning")
    // Do <+signal processing+>
    // Tell runtime system how many input items we consumed on
    // each input stream.
    consume_each(noutput_items);

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
