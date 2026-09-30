/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_FEC_DECODE_H
#define INCLUDED_WISUN_PDU_FEC_DECODE_H

#include <gnuradio/block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief Block to decode the forward error correction of a coded SUN FSK frame.
 * \ingroup wisun
 *
 * This block takes a PDU holding the start-of-frame delimiter followed by the
 * de-whitened code symbols of a FEC-coded frame, deinterleaves and Viterbi-decodes
 * it, and emits a PDU holding the start-of-frame delimiter, the decoded PHY header
 * and the PSDU without its frame check sequence. That is the same layout the
 * uncoded receive path produces, so everything downstream is unaffected.
 *
 * De-whitening is not done here: it happens in the stream domain, ahead of this
 * block, because whitening covers the PSDU's code symbols rather than the decoded
 * data. See docs/sun-fsk-fec.md for the frame layout this expects.
 *
 * Decoding a whole frame per message, rather than in the stream domain, keeps it
 * off the path that acquires the next frame.
 *
 * The following is added to the PDU metadata:
 * - "wisun-fec-metric": the Viterbi path metric, i.e. the number of received bits
 *   the decoder had to overrule. On a clean frame this is zero.
 * - "wisun-fcs-valid": whether the frame check sequence checks out.
 */
class WISUN_API pdu_fec_decode : virtual public gr::block
{
public:
    typedef std::shared_ptr<pdu_fec_decode> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::pdu_fec_decode.
     * \param drop_invalid_frames drop frames whose frame check sequence fails
     *
     * Frames whose path metric is implausibly high are always dropped: such a frame
     * is not a damaged frame, it is not a frame at all, and a frame check sequence
     * alone cannot tell the difference often enough to rely on.
     *
     * To avoid accidental use of raw pointers, wisun::pdu_fec_decode's
     * constructor is in a private implementation
     * class. wisun::pdu_fec_decode::make is the public interface for
     * creating new instances.
     */
    static sptr make(bool drop_invalid_frames = false);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_FEC_DECODE_H */
