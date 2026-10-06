/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_CLIPPING_DETECTOR_C_H
#define INCLUDED_WISUN_CLIPPING_DETECTOR_C_H

#include <gnuradio/sync_block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief Report a clipping receiver input.
 * \ingroup wisun
 *
 * Too much gain does not merely cost packets, it invents them: a clipped burst splatters
 * across the band, and a receiver on a channel megahertz away decodes a weak copy of a
 * frame that was never sent there. Copies have been observed 25 dB below the original,
 * one of them bit-exact and so indistinguishable from a real frame.
 *
 * Clipping has to be seen on the input, before any channel filter: once a channel has been
 * filtered out of a clipped signal its own samples are nowhere near full scale any more.
 * The block is therefore a sink, attached alongside the receive chain rather than in it.
 */
class WISUN_API clipping_detector_c : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<clipping_detector_c> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::clipping_detector_c.
     *
     * \param threshold     magnitude counted as clipping, relative to full scale
     * \param report_period number of samples between reports; a report is only logged if
     *                      samples were clipped during the period
     */
    static sptr make(const float threshold = 0.99f,
                     const uint64_t report_period = 8000000);

    /*!
     * \brief Return the number of samples seen so far.
     */
    virtual uint64_t samples() const = 0;

    /*!
     * \brief Return the number of clipped samples seen so far.
     */
    virtual uint64_t clipped_samples() const = 0;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_CLIPPING_DETECTOR_C_H */
