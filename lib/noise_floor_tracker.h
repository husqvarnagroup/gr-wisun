/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_NOISE_FLOOR_TRACKER_H
#define INCLUDED_WISUN_NOISE_FLOOR_TRACKER_H

#include <gnuradio/filter/single_pole_iir.h>

namespace gr {
namespace wisun {

/*!
 * \brief Smoothed signal power, a tracked noise floor, and a threshold relative to it.
 *
 * Shared by the two relative power squelches, which need exactly this and differ only in
 * what they do with the answer.
 *
 * The noise floor is the lowest smoothed power seen over a long sliding window. Both
 * squelches used to take the lowest power seen since the flow graph started, which is a
 * good estimate that can never recover from a bad one: one deep fade or one quiet stretch
 * latches the floor low for the rest of the run, and since the threshold is derived from
 * it, a later rise of the real noise floor leaves the squelch permanently open. That
 * matters beyond the squelch, because the burst tags it then stops emitting are what
 * tag_based_dc_correction_ff needs in order to re-estimate.
 *
 * A minimum over a window is the smallest change that fixes this. It cannot be dragged
 * upwards by a burst, however long the burst is - which rules out following the power
 * upwards with an IIR, since that closes the squelch in the middle of a long packet - and
 * it forgets a spuriously low reading once the reading leaves the window.
 */
class noise_floor_tracker
{
public:
    /*!
     * \brief Construct a tracker.
     * \param alpha                  smoothing factor of the power estimate; also sets the
     *                               length of the window the minimum is taken over
     * \param relative_threshold_db  threshold above the noise floor, in dB
     */
    noise_floor_tracker(double alpha, double relative_threshold_db);

    /*!
     * \brief Feed one sample's power and update the estimates.
     * \return true if the noise floor estimate changed, for logging
     */
    bool update(double power);

    /*! \brief Whether the smoothed power is at or above the threshold. */
    bool above_threshold() const { return d_pwr >= d_absolute_threshold; }

    double power() const { return d_pwr; }
    double noise_floor() const { return d_noise_floor_pwr; }
    double threshold() const { return d_absolute_threshold; }

    /*! \brief Threshold above the noise floor, in dB. */
    double relative_threshold_db() const;

    /*!
     * \brief Set the threshold above the noise floor.
     * \param db threshold in dB, which has to be positive
     * \throw std::out_of_range if \p db is not positive
     */
    void set_relative_threshold_db(double db);

private:
    /*!
     * \brief Recompute the noise floor from the two half-window minima and the threshold.
     */
    bool update_noise_floor();

    filter::single_pole_iir<double, double, double> d_iir;
    double d_relative_threshold;
    double d_absolute_threshold;
    double d_pwr;
    double d_noise_floor_pwr;

    /*
     * The window minimum is kept as the minimum of the half-window in progress and the
     * minimum of the one before it, each half-window being restarted when it runs out.
     * That gives a minimum over somewhere between one and two half-windows for two
     * doubles and a counter, without a history to search.
     */
    double d_current_half_window_min;
    double d_previous_half_window_min;
    int d_half_window_samples;
    int d_half_window_samples_left;

    int d_settling_samples_left;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_NOISE_FLOOR_TRACKER_H */
