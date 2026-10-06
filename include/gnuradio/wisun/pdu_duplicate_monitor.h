/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_DUPLICATE_MONITOR_H
#define INCLUDED_WISUN_PDU_DUPLICATE_MONITOR_H

#include <gnuradio/block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief Warn when the same frame is received twice at once.
 * \ingroup wisun
 *
 * A transmitter with a spurious sideband puts a copy of its frame on another channel, and
 * a receiver listening there decodes it as a frame of its own. Such a copy has been
 * observed 5 MHz away and 25 dB down, bit-exact and so indistinguishable from the real
 * thing - a corrupted copy at least fails its frame check sequence.
 *
 * This watches for the same frame arriving twice within a short window and says so. It has
 * no output: every frame reaches the consumer whatever this finds, because a sniffer should
 * report what was received and leave the judgement to whoever reads the capture.
 *
 * A retransmission repeats the same bytes too, so the window is what separates the two: a
 * copy of one transmission arrives while the original is still being received, a
 * retransmission a good deal later.
 */
class WISUN_API pdu_duplicate_monitor : virtual public gr::block
{
public:
    typedef std::shared_ptr<pdu_duplicate_monitor> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::pdu_duplicate_monitor.
     *
     * \param window_ms how close in time two identical frames have to be to count as one
     *                  frame received twice rather than a retransmission
     * \param history   number of recent frames to compare against
     */
    static sptr make(const unsigned window_ms = 100, const size_t history = 16);

    /*!
     * \brief Return how many frames were seen a second time.
     */
    virtual uint64_t duplicates() const = 0;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_DUPLICATE_MONITOR_H */
