/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_FEC_H
#define INCLUDED_WISUN_FEC_H

#include <cstddef>
#include <cstdint>
#include <vector>

namespace gr {
namespace wisun {
namespace fec {

/*
 * Forward error correction for SUN FSK, as used by Wi-SUN PHY type 1 (FSK with
 * NRNSC FEC). See docs/sun-fsk-fec.md for how this fits together and for the
 * traps involved; references below are to IEEE 802.15.4-2020.
 *
 * All functions here work on unpacked bits — one bit per byte, in transmission
 * order — and are free of GNU Radio dependencies, so that they can be used both
 * from the sync word correlator (for the PHY header alone) and from the PDU
 * decoder (for a whole frame).
 */

/* number of code symbols in one interleaver block (19.3.6) */
static const size_t interleaver_block_symbols = 16;

/* number of coded bits in one interleaver block (2 bits per code symbol) */
static const size_t interleaver_block_bits = 2 * interleaver_block_symbols;

/* number of octets of PHY header preceding the PSDU */
static const size_t phr_octets = 2;

/*!
 * \brief Undo the block interleaving of 19.3.6.
 *
 * The interleaver permutes whole code symbols within blocks of 16 symbols and
 * keeps no state between blocks, so this is a fixed 16-entry shuffle applied
 * repeatedly.
 *
 * \param in     coded bits in transmission order, n_blocks * 32 of them
 * \param out    deinterleaved coded bits (may not alias \p in)
 * \param n_blocks number of interleaver blocks to process
 */
void deinterleave(const uint8_t* in, uint8_t* out, size_t n_blocks);

/*!
 * \brief Viterbi-decode the rate 1/2 NRNSC convolutional code of 19.3.5.
 *
 * Constraint length 4 with three memory elements, so an 8-state trellis. Both
 * encoder outputs are complemented and u1 is transmitted first. Decoding starts
 * from the zero state, which is where the encoder starts, and traces back from
 * the best surviving state: a frame's padding bits are not necessarily zeros,
 * so the encoder is not necessarily back in the zero state at the end, and this
 * also lets the same code decode the unterminated PHY header on its own.
 *
 * \param code_bits deinterleaved coded bits, 2 * n_symbols of them
 * \param n_symbols number of code symbols to decode
 * \param out       decoded bits, n_symbols of them (may not alias \p code_bits)
 * \return the accumulated path metric of the best survivor, i.e. the number of
 *         received bits the decoder had to overrule — zero for a clean frame,
 *         around a quarter of the code symbols for anything that is not a frame
 */
unsigned viterbi_decode(const uint8_t* code_bits, size_t n_symbols, uint8_t* out);

/*!
 * \brief Return the number of octets a coded frame occupies on air.
 *
 * \param frame_length PSDU length in octets, i.e. what the Frame Length field of
 *                     a coded PHY header carries — roughly half of what arrives
 */
size_t coded_length(uint16_t frame_length);

/*!
 * \brief Check the frame check sequence of a PSDU.
 *
 * \param psdu  complete PSDU, frame check sequence included
 * \param len   length of \p psdu in octets
 * \param fcs16 true for a 2-octet ITU-T CRC-16 seeded with zeroes, false for a
 *              4-octet Ethernet CRC-32
 */
bool fcs_valid(const uint8_t* psdu, size_t len, bool fcs16);

/*!
 * \brief Number of octets the frame check sequence occupies.
 */
static inline size_t fcs_octets(bool fcs16) { return fcs16 ? 2 : 4; }

} /* namespace fec */
} /* namespace wisun */
} /* namespace gr */

#endif /* INCLUDED_WISUN_FEC_H */
