/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "pdu_duplicate_monitor_impl.h"
#include <gnuradio/io_signature.h>
#include <gnuradio/pdu.h>
#include <time.h>

namespace gr {
namespace wisun {

static const pmt::pmt_t pmt_key_channel_number = pmt::string_to_symbol("packet-channel-number");

static uint64_t now_ms()
{
    struct timespec time;
    clock_gettime(CLOCK_MONOTONIC, &time);
    return (uint64_t)time.tv_sec * 1000 + (uint64_t)time.tv_nsec / 1000000;
}

pdu_duplicate_monitor::sptr pdu_duplicate_monitor::make(const unsigned window_ms,
                                                        const size_t history)
{
    return gnuradio::make_block_sptr<pdu_duplicate_monitor_impl>(window_ms, history);
}

pdu_duplicate_monitor_impl::pdu_duplicate_monitor_impl(const unsigned window_ms,
                                                       const size_t history)
    : gr::block("pdu_duplicate_monitor",
                gr::io_signature::make(0, 0, 0),
                gr::io_signature::make(0, 0, 0)),
      d_window_ms(window_ms),
      d_history(history),
      d_duplicates(0)
{
    message_port_register_in(msgport_names::pdus());
    set_msg_handler(msgport_names::pdus(), [this](pmt::pmt_t msg) { this->handle_msg(msg); });
}

pdu_duplicate_monitor_impl::~pdu_duplicate_monitor_impl() {}

void pdu_duplicate_monitor_impl::handle_msg(pmt::pmt_t msg)
{
    if (!pmt::is_pair(msg)) {
        throw std::runtime_error("received a malformed PDU message");
    }

    const pmt::pmt_t meta = pmt::car(msg);
    const std::vector<uint8_t> frame = pmt::u8vector_elements(pmt::cdr(msg));
    const uint64_t arrived_ms = now_ms();
    int16_t channel = -1;
    if (pmt::dict_has_key(meta, pmt_key_channel_number)) {
        channel = (int16_t)pmt::to_long(pmt::cdr(pmt::assoc(pmt_key_channel_number, meta)));
    }

    std::lock_guard<std::mutex> lock(d_mutex);

    for (const auto& earlier : d_recent) {
        /* strictly inside the window, so a window of zero never matches anything */
        if (arrived_ms - earlier.arrived_ms < d_window_ms && earlier.frame == frame) {
            d_duplicates++;
            d_logger->warn("frame on channel {:d} ({:d} octets) was already received "
                           "{:d} ms ago on channel {:d}",
                           channel,
                           frame.size(),
                           arrived_ms - earlier.arrived_ms,
                           earlier.channel);
            break;
        }
    }

    d_recent.push_back({ frame, arrived_ms, channel });
    while (d_recent.size() > d_history) {
        d_recent.pop_front();
    }
}

} /* namespace wisun */
} /* namespace gr */
