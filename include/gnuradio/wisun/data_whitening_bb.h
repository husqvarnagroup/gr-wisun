/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_DATA_WHITENING_BB_H
#define INCLUDED_WISUN_DATA_WHITENING_BB_H

#include <gnuradio/sync_block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief <+description of block+>
 * \ingroup wisun
 *
 */
class WISUN_API data_whitening_bb : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<data_whitening_bb> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::data_whitening_bb.
     *
     * To avoid accidental use of raw pointers, wisun::data_whitening_bb's
     * constructor is in a private implementation
     * class. wisun::data_whitening_bb::make is the public interface for
     * creating new instances.
     */
    static sptr make(const std::string packet_tag, const uint16_t header_bits);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_DATA_WHITENING_BB_H */
