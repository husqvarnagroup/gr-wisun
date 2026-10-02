/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_FCS_CHECK_IMPL_H
#define INCLUDED_WISUN_PDU_FCS_CHECK_IMPL_H

#include <gnuradio/wisun/pdu_fcs_check.h>

namespace gr {
namespace wisun {

class pdu_fcs_check_impl : public pdu_fcs_check
{
private:
    bool d_drop_invalid_frames;

    void handle_msg(pmt::pmt_t msg);

public:
    pdu_fcs_check_impl(bool drop_invalid_frames);
    ~pdu_fcs_check_impl();
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_FCS_CHECK_IMPL_H */
