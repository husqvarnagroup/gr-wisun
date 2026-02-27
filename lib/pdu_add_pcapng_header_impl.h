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
    bool d_prepend_section_header_block;
    bool d_section_header_block_done;
    bool d_prepend_interface_description_block;
    bool d_interface_description_block_done;
    bool d_use_tap_dlt;

public:
    pdu_add_pcapng_header_impl(const bool prepend_section_header_block,
                               const bool prepend_interface_description_block,
                               const bool use_tap_dlt);
    ~pdu_add_pcapng_header_impl();

    void handle_msg(pmt::pmt_t msg);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_IMPL_H */
