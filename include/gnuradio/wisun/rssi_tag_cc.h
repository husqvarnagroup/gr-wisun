/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_RSSI_TAG_CC_H
#define INCLUDED_WISUN_RSSI_TAG_CC_H

#include <gnuradio/sync_block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief <+description of block+>
 * \ingroup wisun
 *
 */
class WISUN_API rssi_tag_cc : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<rssi_tag_cc> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::rssi_tag_cc.
     *
     * To avoid accidental use of raw pointers, wisun::rssi_tag_cc's
     * constructor is in a private implementation
     * class. wisun::rssi_tag_cc::make is the public interface for
     * creating new instances.
     */
    static sptr make(const uint32_t n_samples);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_RSSI_TAG_CC_H */
