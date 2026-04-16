/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_CORRELATE_SYNC_WORD_BB_H
#define INCLUDED_WISUN_CORRELATE_SYNC_WORD_BB_H

#include <gnuradio/sync_block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief Block to detect SFD bit pattern in demodulated bit stream.
 * \ingroup wisun
 *
 * This block is responsible for detecting the start-of-frame delimiter (SFD) within the
 * stream of bits from the demodulated signal. It also extracts the frame length from the
 * packet header (PHR) and adds tag "wisun-packet" containing the frame length to the
 * first bit of the SFD.
 *
 * This block also adds some other tags with extracted information; this is mainly meant
 * for debugging.
 */
class WISUN_API correlate_sync_word_bb : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<correlate_sync_word_bb> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::correlate_sync_word_bb.
     * \param sfd start-of-frame delimiter (2-byte word) to look for
     *
     * To avoid accidental use of raw pointers, wisun::correlate_sync_word_bb's
     * constructor is in a private implementation
     * class. wisun::correlate_sync_word_bb::make is the public interface for
     * creating new instances.
     */
    static sptr make(uint16_t sfd);

    /*!
     * \brief Set RX channel.
     * \param channel RX channel number.
     *
     * The channel is used purely for debugging (include current channel in log messages).
     */
    virtual void set_channel(int16_t channel) = 0;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_CORRELATE_SYNC_WORD_BB_H */
