/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_ADD_PCAP_HEADER_IMPL_H
#define INCLUDED_WISUN_PDU_ADD_PCAP_HEADER_IMPL_H

#include <gnuradio/wisun/pdu_add_pcap_header.h>

namespace gr {
namespace wisun {

class pdu_add_pcap_header_impl : public pdu_add_pcap_header
{
private:
    bool d_prepend_global_pcap_header;
    bool d_global_pcap_header_done;

public:
    pdu_add_pcap_header_impl(const bool prepend_global_pcap_header);
    ~pdu_add_pcap_header_impl();

    void handle_msg(pmt::pmt_t msg);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_ADD_PCAP_HEADER_IMPL_H */
