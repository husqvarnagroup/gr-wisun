/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "clipping_detector_c_impl.h"
#include <gnuradio/io_signature.h>
#include <cmath>

namespace gr {
namespace wisun {

using input_type = gr_complex;

clipping_detector_c::sptr clipping_detector_c::make(const float threshold,
                                                    const uint64_t report_period)
{
    return gnuradio::make_block_sptr<clipping_detector_c_impl>(threshold, report_period);
}

clipping_detector_c_impl::clipping_detector_c_impl(const float threshold,
                                                   const uint64_t report_period)
    : gr::sync_block("clipping_detector_c",
                     gr::io_signature::make(1, 1, sizeof(input_type)),
                     gr::io_signature::make(0, 0, 0)),
      d_threshold(threshold),
      d_report_period(report_period),
      d_samples(0),
      d_clipped_samples(0),
      d_period_samples(0),
      d_period_clipped(0),
      d_reported(false)
{
}

clipping_detector_c_impl::~clipping_detector_c_impl() {}

void clipping_detector_c_impl::report()
{
    if (d_period_clipped == 0 || d_period_samples == 0) {
        d_period_samples = 0;
        return;
    }

    /*
     * The first report says what to do about it; later ones only keep count, since a gain
     * that is too high stays too high and the message would otherwise repeat in full.
     */
    if (d_reported) {
        d_logger->warn("input still clipping: {:.3f} % of the last {:d} samples",
                       100.0 * (double)d_period_clipped / (double)d_period_samples,
                       d_period_samples);
    } else {
        d_logger->warn("input is clipping: {:.3f} % of the last {:d} samples reach full "
                       "scale. Reduce the receiver gain - a clipped burst splatters across "
                       "the band and can be decoded again on channels it was never sent on",
                       100.0 * (double)d_period_clipped / (double)d_period_samples,
                       d_period_samples);
        d_reported = true;
    }

    d_period_samples = 0;
    d_period_clipped = 0;
}

bool clipping_detector_c_impl::stop()
{
    report();
    return true;
}

int clipping_detector_c_impl::work(int noutput_items,
                                   gr_vector_const_void_star& input_items,
                                   gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);

    for (int i = 0; i < noutput_items; i++) {
        /* either component reaching full scale is clipping, whatever the other one does */
        if (std::fabs(in[i].real()) >= d_threshold || std::fabs(in[i].imag()) >= d_threshold) {
            d_clipped_samples++;
            d_period_clipped++;
        }
    }
    d_samples += noutput_items;
    d_period_samples += noutput_items;

    if (d_period_samples >= d_report_period) {
        report();
    }

    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
