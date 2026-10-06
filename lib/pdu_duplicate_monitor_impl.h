/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_DUPLICATE_MONITOR_IMPL_H
#define INCLUDED_WISUN_PDU_DUPLICATE_MONITOR_IMPL_H

#include <gnuradio/wisun/pdu_duplicate_monitor.h>
#include <deque>
#include <mutex>
#include <vector>

namespace gr {
namespace wisun {

class pdu_duplicate_monitor_impl : public pdu_duplicate_monitor
{
private:
    struct seen_frame {
        std::vector<uint8_t> frame;
        uint64_t arrived_ms;
        int16_t channel;
    };

    const unsigned d_window_ms;
    const size_t d_history;

    /* every channel receiver publishes into the one input port, from its own thread */
    std::mutex d_mutex;
    std::deque<seen_frame> d_recent;
    uint64_t d_duplicates;

    void handle_msg(pmt::pmt_t msg);

public:
    pdu_duplicate_monitor_impl(const unsigned window_ms, const size_t history);
    ~pdu_duplicate_monitor_impl();

    uint64_t duplicates() const override { return d_duplicates; }
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_DUPLICATE_MONITOR_IMPL_H */
