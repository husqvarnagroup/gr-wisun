/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "data_whitening_bb_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace wisun {

static const uint16_t pn9_seed = 0x1ff;

using input_type = uint8_t;
using output_type = uint8_t;

data_whitening_bb::sptr data_whitening_bb::make(const std::string packet_tag,
                                                const uint16_t header_bits)
{
    return gnuradio::make_block_sptr<data_whitening_bb_impl>(packet_tag, header_bits);
}


/*
 * The private constructor
 */
data_whitening_bb_impl::data_whitening_bb_impl(const std::string packet_tag,
                                               const uint16_t header_bits)
    : gr::sync_block("data_whitening_bb",
                     gr::io_signature::make(1, 1, sizeof(input_type)),
                     gr::io_signature::make(1, 1, sizeof(output_type))),
      d_packet_tag_key(pmt::string_to_symbol(packet_tag)),
      d_header_bits(header_bits),
      d_header_bits_remaining(0),
      d_payload_bits_remaining(0),
      d_pn9_state(0)
{
}

/*
 * Our virtual destructor.
 */
data_whitening_bb_impl::~data_whitening_bb_impl() {}

void data_whitening_bb_impl::start_packet(long packet_octets)
{
    const long packet_bits = 8 * packet_octets;

    if (packet_bits <= d_header_bits) {
        d_logger->warn("ignoring packet of {:d} octets: too short to hold the "
                       "{:d} header bits",
                       packet_octets,
                       d_header_bits);
        d_header_bits_remaining = 0;
        d_payload_bits_remaining = 0;
        return;
    }

    d_header_bits_remaining = d_header_bits;
    d_payload_bits_remaining = (int)(packet_bits - d_header_bits);
    d_pn9_state = pn9_seed;
}

int data_whitening_bb_impl::work(int noutput_items,
                                 gr_vector_const_void_star& input_items,
                                 gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);

    /* TODO check if data whitening is enabled for each packet */

    /* find all packet tags in this window */
    std::vector<tag_t> tags;
    get_tags_in_range(
        tags, 0, nitems_read(0), nitems_read(0) + noutput_items, d_packet_tag_key);
    size_t next_tag = 0;

    // do signal processing
    for (int i = 0; i < noutput_items; i++) {
        /*
         * packet tag starts de-whitening from the beginning, wherever in a previous
         * packet we happen to be
         */
        while (next_tag < tags.size() &&
               tags[next_tag].offset == nitems_read(0) + (uint64_t)i) {
            start_packet(pmt::to_long(tags[next_tag].value));
            next_tag++;
        }

        if (d_header_bits_remaining) { /* ignore packet header (no data whitening) */
            out[i] = in[i];
            d_header_bits_remaining--;
        } else if (d_payload_bits_remaining) { /* apply data whitening to payload */
            /* update PN9 state */
            const uint16_t pn9_next_bit = ((d_pn9_state >> 8) ^ (d_pn9_state >> 3)) & 1;
            d_pn9_state = ((d_pn9_state << 1) | pn9_next_bit) & 0x1ff;
            /* apply whitening to next bit */
            out[i] = in[i] ^ pn9_next_bit;
            d_payload_bits_remaining--;
        } else {
            /* copy unmodified data */
            out[i] = in[i];
        }
    }

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace wisun */
} /* namespace gr */
