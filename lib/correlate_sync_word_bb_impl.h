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
    bool d_fec;

    int d_preamble_bit_counter;
    uint8_t d_preamble_last_bit;
    uint16_t d_sfd_data;
    uint32_t d_phr_data;
    int16_t d_channel;
    bool d_outside_channel_mask;

    /*!
     * \brief Decode the PHY header of a coded frame from its code bits.
     *
     * The PHY header of a coded frame is exactly the first interleaver block and
     * is not whitened, so it can be deinterleaved and decoded on its own,
     * straight off the first 4 octets after the SFD.
     *
     * \param code_bits 32 code bits in transmission order
     * \param metric    accumulated path metric of the decode, for plausibility checks
     * \return the PHY header, as a 16-bit value assembled most significant bit first
     */
    uint16_t decode_coded_phr(const uint8_t* code_bits, unsigned& metric);

public:
    correlate_sync_word_bb_impl(uint16_t sfd, bool fec);
    ~correlate_sync_word_bb_impl();

    void set_channel(int16_t channel) override { d_channel = channel; }

    void set_outside_channel_mask(bool outside) override
    {
        d_outside_channel_mask = outside;
    }

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items) override;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_CORRELATE_SYNC_WORD_BB_IMPL_H */
