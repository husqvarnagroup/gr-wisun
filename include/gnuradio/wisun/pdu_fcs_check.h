/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_FCS_CHECK_H
#define INCLUDED_WISUN_PDU_FCS_CHECK_H

#include <gnuradio/block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief Block to validate the frame check sequence of an uncoded SUN FSK frame.
 * \ingroup wisun
 *
 * This block takes a PDU holding the start-of-frame delimiter, the PHY header and
 * the de-whitened PSDU of an uncoded frame, checks the frame check sequence, and
 * emits a PDU holding the start-of-frame delimiter, the PHY header and the PSDU
 * without its frame check sequence. That is the same layout pdu_fec_decode
 * produces for a coded frame, so everything downstream is unaffected by whether a
 * frame was coded or not.
 *
 * The uncoded receive path has no decoding step to do this as a side effect of
 * decoding, unlike the coded path, which is why this exists as a separate block.
 *
 * The following is added to the PDU metadata:
 * - "wisun-fcs-valid": whether the frame check sequence checks out.
 */
class WISUN_API pdu_fcs_check : virtual public gr::block
{
public:
    typedef std::shared_ptr<pdu_fcs_check> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::pdu_fcs_check.
     * \param drop_invalid_frames drop frames whose frame check sequence fails
     *
     * To avoid accidental use of raw pointers, wisun::pdu_fcs_check's
     * constructor is in a private implementation
     * class. wisun::pdu_fcs_check::make is the public interface for
     * creating new instances.
     */
    static sptr make(bool drop_invalid_frames = false);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_FCS_CHECK_H */
