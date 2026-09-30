/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "fec.h"

namespace gr {
namespace wisun {
namespace fec {

/* number of trellis states: three memory elements (19.3.5) */
static const size_t n_states = 8;

/* a metric no survivor can reach, used for states not yet reachable */
static const unsigned metric_unreachable = 0xffffffff;

/*
 * Interleaver permutation of 19.3.6: the code symbol transmitted k-th was taken
 * from position t = 15 - 4 * (k mod 4) - floor(k / 4).
 */
static inline size_t interleaver_source(size_t k) { return 15 - 4 * (k % 4) - k / 4; }

void deinterleave(const uint8_t* in, uint8_t* out, size_t n_blocks)
{
    for (size_t block = 0; block < n_blocks; block++) {
        const size_t base = block * interleaver_block_bits;
        for (size_t k = 0; k < interleaver_block_symbols; k++) {
            /* the symbol received k-th belongs at position t */
            const size_t t = interleaver_source(k);
            out[base + 2 * t] = in[base + 2 * k];
            out[base + 2 * t + 1] = in[base + 2 * k + 1];
        }
    }
}

unsigned viterbi_decode(const uint8_t* code_bits, size_t n_symbols, uint8_t* out)
{
    /*
     * The state holds the three previous input bits, b(i-1) in the least
     * significant position:
     *
     *   u1(i) = NOT ( b(i) XOR b(i-2) XOR b(i-3) )           G1 = 1 + x² + x³
     *   u0(i) = NOT ( b(i) XOR b(i-1) XOR b(i-2) XOR b(i-3) ) G0 = 1 + x + x² + x³
     *
     * Both outputs are complemented; omitting that inverts every recovered bit.
     */
    uint8_t next_state[n_states][2];
    uint8_t output[n_states][2][2];
    for (size_t state = 0; state < n_states; state++) {
        const uint8_t b1 = state & 1;
        const uint8_t b2 = (state >> 1) & 1;
        const uint8_t b3 = (state >> 2) & 1;
        for (uint8_t bit = 0; bit < 2; bit++) {
            next_state[state][bit] = bit | (b1 << 1) | (b2 << 2);
            output[state][bit][0] = 1 ^ bit ^ b2 ^ b3;      /* u1, sent first */
            output[state][bit][1] = 1 ^ bit ^ b1 ^ b2 ^ b3; /* u0 */
        }
    }

    /* survivor bookkeeping: for every stage and state, the predecessor state */
    std::vector<uint8_t> traceback(n_symbols * n_states);

    unsigned metric[n_states];
    unsigned new_metric[n_states];
    /* the encoder starts in the zero state */
    for (size_t state = 0; state < n_states; state++) {
        metric[state] = (state == 0) ? 0 : metric_unreachable;
    }

    for (size_t i = 0; i < n_symbols; i++) {
        const uint8_t r1 = code_bits[2 * i];
        const uint8_t r0 = code_bits[2 * i + 1];
        for (size_t state = 0; state < n_states; state++) {
            new_metric[state] = metric_unreachable;
        }
        for (size_t state = 0; state < n_states; state++) {
            if (metric[state] == metric_unreachable) {
                continue;
            }
            for (uint8_t bit = 0; bit < 2; bit++) {
                const uint8_t next = next_state[state][bit];
                const unsigned candidate = metric[state] + (output[state][bit][0] != r1) +
                                           (output[state][bit][1] != r0);
                if (candidate < new_metric[next]) {
                    new_metric[next] = candidate;
                    traceback[i * n_states + next] = (uint8_t)state;
                }
            }
        }
        for (size_t state = 0; state < n_states; state++) {
            metric[state] = new_metric[state];
        }
    }

    /*
     * Trace back from the best surviving state rather than from state 0: the
     * padding bits are not necessarily zeros, so a complete frame does not
     * necessarily end in the zero state, and the PHY header decode is not
     * terminated at all.
     */
    size_t state = 0;
    for (size_t s = 1; s < n_states; s++) {
        if (metric[s] < metric[state]) {
            state = s;
        }
    }
    const unsigned best_metric = metric[state];

    for (size_t i = n_symbols; i-- > 0;) {
        /* the bit fed in at this stage is b(i-1) of the state it led to */
        out[i] = state & 1;
        state = traceback[i * n_states + state];
    }

    return best_metric;
}

size_t coded_length(uint16_t frame_length)
{
    /*
     * After PHR + PSDU + 3 tail bits the block is padded to a whole number of
     * 16-bit interleaver blocks, which is the same as saying that tail and
     * padding together occupy one whole octet when PHR + PSDU is an odd number
     * of octets and two when it is even (19.3.5). At rate 1/2 that doubles.
     */
    const size_t octets = frame_length + phr_octets;
    return (octets + (octets % 2 ? 1 : 2)) * 2;
}

bool fcs_valid(const uint8_t* psdu, size_t len, bool fcs16)
{
    const size_t width = fcs_octets(fcs16);
    if (len < width) {
        return false;
    }

    uint32_t received = 0;
    /* the frame check sequence is transmitted least significant octet first */
    for (size_t i = 0; i < width; i++) {
        received |= (uint32_t)psdu[len - width + i] << (8 * i);
    }

    if (fcs16) {
        /* ITU-T CRC-16 seeded with zeroes */
        uint16_t crc = 0;
        for (size_t i = 0; i < len - width; i++) {
            crc ^= psdu[i];
            for (int bit = 0; bit < 8; bit++) {
                crc = (crc >> 1) ^ ((crc & 1) ? 0x8408 : 0);
            }
        }
        return crc == (uint16_t)received;
    }

    /* the ordinary Ethernet CRC-32: reflected, seeded and inverted with all ones */
    uint32_t crc = 0xffffffff;
    for (size_t i = 0; i < len - width; i++) {
        crc ^= psdu[i];
        for (int bit = 0; bit < 8; bit++) {
            crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
        }
    }
    crc ^= 0xffffffff;
    return crc == received;
}

} /* namespace fec */
} /* namespace wisun */
} /* namespace gr */
