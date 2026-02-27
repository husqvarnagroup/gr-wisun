/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_IMPL_H
#define INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_IMPL_H

#include <gnuradio/wisun/pdu_add_pcapng_header.h>

namespace gr {
namespace wisun {

class pdu_add_pcapng_header_impl : public pdu_add_pcapng_header
{
private:
    // Nothing to declare in this block.

public:
    pdu_add_pcapng_header_impl(const bool prepend_section_header_block,
                               const bool prepend_interface_description_block);
    ~pdu_add_pcapng_header_impl();

    // Where all the action really happens
    void forecast(int noutput_items, gr_vector_int& ninput_items_required);

    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_IMPL_H */
