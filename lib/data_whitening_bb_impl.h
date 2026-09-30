/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_DATA_WHITENING_BB_IMPL_H
#define INCLUDED_WISUN_DATA_WHITENING_BB_IMPL_H

#include <gnuradio/wisun/data_whitening_bb.h>

namespace gr {
namespace wisun {

class data_whitening_bb_impl : public data_whitening_bb
{
private:
    pmt::pmt_t d_packet_tag_key;
    int d_header_bits;
    int d_header_bits_remaining;
    int d_payload_bits_remaining;
    uint16_t d_pn9_state;

    /*!
     * \brief Set up de-whitening for a packet of the given length.
     *
     * A packet too short to hold the header is skipped rather than de-whitened: the
     * length comes from a PHY header that nothing has checked, and subtracting the
     * header from it unchecked used to wrap around and de-whiten tens of thousands of
     * following bits.
     *
     * \param packet_octets packet length in octets, from the packet tag
     */
    void start_packet(long packet_octets);

public:
    data_whitening_bb_impl(const std::string packet_tag, const uint16_t header_bits);
    ~data_whitening_bb_impl();

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items) override;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_DATA_WHITENING_BB_IMPL_H */
