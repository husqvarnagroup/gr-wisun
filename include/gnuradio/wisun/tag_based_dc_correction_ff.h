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
 * \brief <+description of block+>
 * \ingroup wisun
 *
 */
class WISUN_API tag_based_dc_correction_ff : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<tag_based_dc_correction_ff> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::tag_based_dc_correction_ff.
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
