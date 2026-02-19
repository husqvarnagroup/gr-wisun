/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_TAG_BASED_DC_CORRECTION_FF_H
#define INCLUDED_WISUN_TAG_BASED_DC_CORRECTION_FF_H

#include <gnuradio/sync_block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief Block to correct DC offset of received FSK signal based on estimation from preamble.
 * \ingroup wisun
 *
 * This block can be used to remove a DC offset after the frequency demodulation. This
 * helps with clock synchronization & bit mapping later on.
 *
 * Ideally, the signal after frequency demodulation would be centered around zero, since
 * the upper and lower frequency should have the same distance from the center frequency.
 * However, if there is an offset in the center frequency, this results in an offset after
 * demodulation. Since the preamble alternates between ones and zeroes, we can directly
 * use the average of the demodulated preamble for offset correction (i.e. doing channel
 * estimation, which is part of the reason for the preamble to begin with).
 *
 * If the frequency offset is sufficiently small (i.e. clock sources on both sides are
 * fairly accurate), this block is not required.
 *
 * In contrast to the dc_correction_ff block, this block relies on existing tags (e.g.
 * from power squelch block) to determine the start and end of the signal. This is more
 * efficient and more sensible, as measuring the power of the demodulated signal only
 * works due to the power squelch block (without the squelch block, the power of
 * demodulated noise would actually be higher than that of the actual signal).
 */
class WISUN_API tag_based_dc_correction_ff : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<tag_based_dc_correction_ff> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::tag_based_dc_correction_ff.
     * \param signal_start_tag Name of tag indicating start of signal
     * \param signal_end_tag Name of tag indicating end of signal
     * \param estimation_length Number of samples to use for DC offset estimation. The
     * length should be chosen large enough to have a good estimation, but small enough to
     * start correction early enough to still have a sufficient number of corrected
     * preamble bits for sync word correlation. As a rule of thumb, use 1/4 of the
     * preamble.
     *
     * To avoid accidental use of raw pointers, wisun::tag_based_dc_correction_ff's
     * constructor is in a private implementation
     * class. wisun::tag_based_dc_correction_ff::make is the public interface for
     * creating new instances.
     */
    static sptr make(const std::string signal_start_tag,
                     const std::string signal_end_tag,
                     const int estimation_length);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_TAG_BASED_DC_CORRECTION_FF_H */
