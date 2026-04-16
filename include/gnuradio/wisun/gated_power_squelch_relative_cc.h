/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_H
#define INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_H

#include <gnuradio/block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief Gated variant of power_squelch_relative_cc block (truncates samples after power
 * drops below threshold).
 * \ingroup wisun
 *
 */
class WISUN_API gated_power_squelch_relative_cc : virtual public gr::block
{
public:
    typedef std::shared_ptr<gated_power_squelch_relative_cc> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of
     * wisun::gated_power_squelch_relative_cc.
     * \param relative_threshold Relative threshold for signal level above noise floor in
     * dB (i.e. this is the threshold to *unsquelch* and should be a positive number).
     * \param alpha Gain of averaging filter.
     * \param trailing_samples Number of trailing samples after signal drops below
     * threshold. May be needed to make sure downstream blocks have enough samples to
     * process the packet (otherwise, packets may only be processed once the next packet
     * arrives).
     *
     * To avoid accidental use of raw pointers, wisun::gated_power_squelch_relative_cc's
     * constructor is in a private implementation
     * class. wisun::gated_power_squelch_relative_cc::make is the public interface for
     * creating new instances.
     */
    static sptr
    make(const double relative_threshold, const double alpha, const int trailing_samples);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_GATED_POWER_SQUELCH_RELATIVE_CC_H */
