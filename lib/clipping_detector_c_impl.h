/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_CLIPPING_DETECTOR_C_IMPL_H
#define INCLUDED_WISUN_CLIPPING_DETECTOR_C_IMPL_H

#include <gnuradio/wisun/clipping_detector_c.h>

namespace gr {
namespace wisun {

class clipping_detector_c_impl : public clipping_detector_c
{
private:
    const float d_threshold;
    const uint64_t d_report_period;

    uint64_t d_samples;
    uint64_t d_clipped_samples;
    /* counts within the period not yet reported */
    uint64_t d_period_samples;
    uint64_t d_period_clipped;
    bool d_reported;

    void report();

public:
    clipping_detector_c_impl(const float threshold, const uint64_t report_period);
    ~clipping_detector_c_impl();

    uint64_t samples() const override { return d_samples; }

    uint64_t clipped_samples() const override { return d_clipped_samples; }

    /* log what was seen in a period that ends with the flow graph rather than with a report */
    bool stop() override;

    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items) override;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_CLIPPING_DETECTOR_C_IMPL_H */
