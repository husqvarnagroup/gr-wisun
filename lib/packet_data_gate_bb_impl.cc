/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "packet_data_gate_bb_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

/*
 * relative threshold in dB for detecting truncated packets
 *
 * Note: this value should be chosen conservatively, rather too high than too low:
 * a) the impact of a false positive (truncate a good packet) is higher than that of a
 *    false negative (not truncate a bad packet); for a not truncated bad packet
 *    we will still only receive the number of bits from the length tag (which could be
 *    too high for an invalid packet, but is already truncated to maximum packet length)
 *    and Wireshark will later detect the invalid packet due to the incorrect checksum.
 * b) since most packets are generally good (unless we detected a packet where there is
 *    none), the chance for a false positive is higher.
 */
static const double phy_relative_rssi_threshold = 25;

using input_type = uint8_t;
using output_type = uint8_t;

packet_data_gate_bb::sptr packet_data_gate_bb::make(const std::string length_tag)
{
    return gnuradio::make_block_sptr<packet_data_gate_bb_impl>(length_tag);
}


/*
 * The private constructor
 */
packet_data_gate_bb_impl::packet_data_gate_bb_impl(const std::string length_tag)
    : gr::block("packet_data_gate_bb",
                gr::io_signature::make(1, 1, sizeof(input_type)),
                gr::io_signature::make(1, 1, sizeof(output_type))),
      d_length_tag(length_tag),
      d_remaining_samples(0),
      d_packet_rssi_tag_done(false),
      d_packet_rssi_first_tag_discarded(false),
      d_packet_rssi_threshold_warning_done(false),
      d_current_packet_absolute_offset(0),
      d_packet_rssi(0),
      d_channel(-1)
{
    /* disable tag propagation (we propagate tags manually to adjust any offset) */
    set_tag_propagation_policy(TPP_DONT);
}


/*
 * Our virtual destructor.
 */
packet_data_gate_bb_impl::~packet_data_gate_bb_impl() {}

void packet_data_gate_bb_impl::forecast(int noutput_items,
                                        gr_vector_int& ninput_items_required)
{
    /* we produce a lot fewer samples than we get, but the actual ratio depends on the
     * number of packets received, so no way to predict */
    ninput_items_required[0] = noutput_items * 10;
}

int packet_data_gate_bb_impl::general_work(int noutput_items,
                                           gr_vector_int& ninput_items,
                                           gr_vector_const_void_star& input_items,
                                           gr_vector_void_star& output_items)
{
    std::vector<tag_t> tags;

    if (d_remaining_samples == 0) { /* look for length tag; discard up to length tag */
        /* look for length tag */
        get_tags_in_range(tags,
                          0,
                          nitems_read(0),
                          nitems_read(0) + ninput_items[0],
                          pmt::string_to_symbol(d_length_tag));
        if (tags.size() == 0) { /* no length tag; discard everything */
            consume(0, ninput_items[0]);
        } else { /* length tag found; discard up to length tag */
            /* note: length is in bytes – we need 8 * length samples */
            d_remaining_samples = 8 * pmt::to_long(tags[0].value);
            d_packet_rssi_tag_done = false;
            d_packet_rssi_first_tag_discarded = false;
            d_packet_rssi_threshold_warning_done = false;
            d_current_packet_absolute_offset = nitems_written(0);
            consume(0, tags[0].offset - nitems_read(0));
        }
        /* nothing was produced */
        return 0;
    } else { /* process as many samples as possible */
        /* determine number of samples to process */
        int num_to_process = std::min(d_remaining_samples, ninput_items[0]);
        int current_tag_offset = nitems_read(0) - nitems_written(0);
        /* propagate tags manually, adjusting offset */
        get_tags_in_range(tags, 0, nitems_read(0), nitems_read(0) + num_to_process);
        for (size_t i = 0; i < tags.size(); i++) {
            gr::tag_t t = tags[i];
            t.offset -= current_tag_offset;
            add_item_tag(0, t);
            /* handle RSSI tags separately (to add new tag "packet-rssi") */
            if (pmt::equal(t.key, pmt::string_to_symbol("rssi"))) {
                double rssi = pmt::to_double(t.value);
                // std::cerr << "RSSI tag: "
                //           << std::to_string(pmt::to_double(t.value))
                //           << " dB; offset within packet " << std::to_string(t.offset -
                //           d_current_packet_absolute_offset)
                //           << ")" << std::endl;
                if (!d_packet_rssi_tag_done) {
                    /*
                     * We use the second RSSI tag as RSSI for whole packet. Since the
                     * preamble is quite short in Wi-SUN, the calculation for the first
                     * RSSI tag may be based partly on data before the start of the
                     * preamble (i.e. when there was no transmission in the air, making
                     * the first calculated RSSI value too low).
                     */
                    if (!d_packet_rssi_first_tag_discarded) {
                        d_packet_rssi_first_tag_discarded = true;
                    } else {
                        // std::cout << "adding as packet RSSI tag" << std::endl;
                        gr::block::add_item_tag(0,
                                                this->nitems_written(0),
                                                pmt::string_to_symbol("packet-rssi"),
                                                t.value);
                        d_packet_rssi_tag_done = true;
                        d_packet_rssi = rssi;
                    }
                } else if (!d_packet_rssi_threshold_warning_done &&
                           rssi < d_packet_rssi - phy_relative_rssi_threshold) {
                    /* warn (once per packet) if RSSI below threshold */
                    int low_rssi_offset = t.offset - d_current_packet_absolute_offset;
                    d_logger->warn("low RSSI during packet data (channel: {:d}, "
                                   "RSSI: {:f}, bit offset: {:d})",
                                   d_channel, rssi, low_rssi_offset);
                    d_packet_rssi_threshold_warning_done = true;
                    gr::block::add_item_tag(0,
                                            t.offset,
                                            pmt::string_to_symbol("packet-truncated"),
                                            pmt::from_long(low_rssi_offset));
                }
            }
        }
        /* copy samples */
        memcpy(output_items[0], input_items[0], num_to_process);
        /* tell runtime system how many input items we consumed */
        consume(0, num_to_process);
        /* track remaining samples in packet */
        d_remaining_samples -= num_to_process;
        /* tell runtime system how many output items we produced. */
        return num_to_process;
    }
}

} /* namespace wisun */
} /* namespace gr */
