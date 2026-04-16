/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PACKET_DATA_GATE_BB_IMPL_H
#define INCLUDED_WISUN_PACKET_DATA_GATE_BB_IMPL_H

#include <gnuradio/wisun/packet_data_gate_bb.h>

namespace gr {
namespace wisun {

class packet_data_gate_bb_impl : public packet_data_gate_bb
{
private:
    std::string d_length_tag;
    int d_remaining_samples;
    bool d_packet_rssi_tag_done;
    bool d_packet_rssi_first_tag_discarded;
    bool d_packet_rssi_threshold_warning_done;
    int d_current_packet_absolute_offset;
    double d_packet_rssi;
    int16_t d_channel;

public:
    packet_data_gate_bb_impl(const std::string length_tag);
    ~packet_data_gate_bb_impl();

    void set_channel(int16_t channel) override { d_channel = channel; }

    // Where all the action really happens
    void forecast(int noutput_items, gr_vector_int& ninput_items_required) override;

    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items) override;
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PACKET_DATA_GATE_BB_IMPL_H */
