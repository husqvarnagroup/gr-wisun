/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_CORRELATE_SYNC_WORD_BB_IMPL_H
#define INCLUDED_WISUN_CORRELATE_SYNC_WORD_BB_IMPL_H

#include <gnuradio/wisun/correlate_sync_word_bb.h>

namespace gr {
namespace wisun {

class correlate_sync_word_bb_impl : public correlate_sync_word_bb
{
private:
    uint16_t d_sfd;

    int d_preamble_bit_counter;
    uint8_t d_preamble_last_bit;
    uint16_t d_sfd_data;
    uint16_t d_phr_data;
    int16_t d_channel;

public:
    correlate_sync_word_bb_impl(uint16_t sfd);
    ~correlate_sync_word_bb_impl();

    void set_channel(int16_t channel) override { d_channel = channel; }

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items) override;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_CORRELATE_SYNC_WORD_BB_IMPL_H */
