/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "noise_floor_tracker.h"
#include <cmath>
#include <limits>
#include <stdexcept>

namespace gr {
namespace wisun {

/*
 * How many time constants of the power estimate to wait before the noise floor is tracked
 * at all, so that an estimate still on its way from an arbitrary starting value is not
 * taken for the noise.
 *
 * One time constant leaves the estimate well short of settled, and waiting five was tried
 * here on the grounds that it would give a truer first reading. It measurably cost
 * packets on the recorded samples - the decode rate near the sensitivity limit dropped by
 * up to 0.17 across four of the five recordings - so it is left as it was.
 */
static const double settling_time_constants = 1;

/*
 * Length of each half of the sliding window the minimum is taken over, in time constants
 * of the power estimate. The window is what sets how long a spuriously low reading keeps
 * the threshold down, so it wants to be short; but a window holding nothing but signal
 * would take the floor up to the signal level and close the squelch mid-packet, so it has
 * to be comfortably longer than the longest transmission.
 *
 * The alpha the receive chain uses puts a time constant at a hundred samples, so this is
 * a window of one to two million samples: at the sample rates in use, something between
 * one and a few seconds. The longest SUN FSK frame is a third of a second, so any real
 * traffic leaves idle time inside the window, and recovery from a bad estimate takes
 * seconds rather than the rest of the run.
 */
static const double half_window_time_constants = 10000;

noise_floor_tracker::noise_floor_tracker(double alpha, double relative_threshold_db)
    : d_iir(alpha),
      d_pwr(1),
      d_noise_floor_pwr(1),
      d_current_half_window_min(std::numeric_limits<double>::infinity()),
      d_previous_half_window_min(std::numeric_limits<double>::infinity()),
      d_half_window_samples((int)(half_window_time_constants / alpha)),
      d_half_window_samples_left((int)(half_window_time_constants / alpha)),
      d_settling_samples_left((int)(settling_time_constants / alpha))
{
    set_relative_threshold_db(relative_threshold_db);
}

double noise_floor_tracker::relative_threshold_db() const
{
    return 10 * std::log10(d_relative_threshold);
}

void noise_floor_tracker::set_relative_threshold_db(double db)
{
    if (db <= 0) {
        throw std::out_of_range("relative_threshold db must be > 0\n");
    }

    d_relative_threshold = std::pow(10.0, db / 10);
    d_absolute_threshold = d_noise_floor_pwr * d_relative_threshold;
}

bool noise_floor_tracker::update_noise_floor()
{
    const double previous = d_noise_floor_pwr;

    d_noise_floor_pwr = std::min(d_current_half_window_min, d_previous_half_window_min);
    d_absolute_threshold = d_noise_floor_pwr * d_relative_threshold;

    return d_noise_floor_pwr != previous;
}

bool noise_floor_tracker::update(double power)
{
    d_pwr = d_iir.filter(power);

    if (d_settling_samples_left > 0) {
        /* the power estimate is not evidence about the noise until it has settled */
        d_settling_samples_left--;
        return false;
    }

    if (d_pwr < d_current_half_window_min) {
        d_current_half_window_min = d_pwr;
    }

    if (--d_half_window_samples_left == 0) {
        /* retire the older half-window and start a new one */
        d_previous_half_window_min = d_current_half_window_min;
        d_current_half_window_min = std::numeric_limits<double>::infinity();
        d_half_window_samples_left = d_half_window_samples;
    }

    return update_noise_floor();
}

} /* namespace wisun */
} /* namespace gr */
