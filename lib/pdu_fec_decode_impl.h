/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_FEC_DECODE_IMPL_H
#define INCLUDED_WISUN_PDU_FEC_DECODE_IMPL_H

#include <gnuradio/wisun/pdu_fec_decode.h>

namespace gr {
namespace wisun {

class pdu_fec_decode_impl : public pdu_fec_decode
{
private:
    bool d_drop_invalid_frames;

    void handle_msg(pmt::pmt_t msg);

public:
    pdu_fec_decode_impl(bool drop_invalid_frames);
    ~pdu_fec_decode_impl();
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_FEC_DECODE_IMPL_H */
