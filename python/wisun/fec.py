# coding: utf-8
#
# Copyright (c) 2026 Gardena GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# References:
# [802.15.4] IEEE 802.15.4-2020

"""Reference encoder for FEC-coded SUN FSK (NRNSC).

This module is a plain-Python model of what a transmitter does to build a
coded frame, written from the standard rather than by inverting the decoder in
``lib/fec.cc``. Keeping the two independent is what makes it worth testing one
against the other; see ``docs/sun-fsk-fec.md``.

Bit lists are used throughout, one bit per list element, in transmission order.
The whole module is free of GNU Radio and numpy dependencies, so it also serves
as a readable reference on its own.
"""

# [802.15.4] 19.2.3, Table 19-2: start-of-frame delimiter for phySunFskSfd = 0
SFD_UNCODED = 0x904E
SFD_CODED = 0x6F4E

# The preamble is an alternating bit pattern ([802.15.4] 19.2.2). On air it runs
# 0101... and ends on a 1, immediately before the SFD, which is what a correlator
# looking for the end of the preamble keys on; as an octet transmitted least
# significant bit first, that pattern is 0xaa.
PREAMBLE_OCTET = 0xAA
PREAMBLE_OCTETS = 8

# [802.15.4] 19.3.6: the interleaver operates on blocks of 16 code symbols
INTERLEAVER_BLOCK_SYMBOLS = 16

# [802.15.4] 19.3.5: the convolutional code is terminated with 3 zero bits
TAIL_BITS = 3

# number of octets of PHY header preceding the PSDU
PHR_OCTETS = 2


def octets_to_bits(octets):
    """Convert octets to a bit list, least significant bit of each octet first."""
    return [(octet >> i) & 1 for octet in octets for i in range(8)]


def bits_to_octets(bits):
    """Convert a bit list to octets, least significant bit of each octet first."""
    assert len(bits) % 8 == 0, "expected a whole number of octets"
    return bytes(sum(bits[8 * i + j] << j for j in range(8)) for i in range(len(bits) // 8))


def bits_msb_first(value, width):
    """Convert an integer to a bit list, most significant bit first."""
    return [(value >> i) & 1 for i in reversed(range(width))]


def value_msb_first(bits):
    """Convert a bit list to an integer, treating the first bit as most significant."""
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def pn9_sequence(length):
    """Return the first `length` bits of the PN9 whitening sequence.

    The generator polynomial is x⁹ + x⁵ + 1, seeded with all ones. The bit that
    comes out is the feedback term itself rather than a bit of the register,
    which is what makes the sequence open with 0000 1111 0111 ([802.15.4]
    16.2.3).
    """
    state = 0x1FF
    sequence = []
    for _ in range(length):
        feedback = ((state >> 8) ^ (state >> 3)) & 1
        state = ((state << 1) | feedback) & 0x1FF
        sequence.append(feedback)
    return sequence


def convolutional_encode(bits):
    """Encode a bit list with the NRNSC code and return the code bits.

    Rate 1/2, constraint length 4, non-recursive non-systematic ([802.15.4]
    19.3.5). Both outputs are complemented, and u1 is transmitted first.
    """
    b1 = b2 = b3 = 0
    code_bits = []
    for bit in bits:
        code_bits.append(1 ^ bit ^ b2 ^ b3)            # u1, G1 = 1 + x² + x³
        code_bits.append(1 ^ bit ^ b1 ^ b2 ^ b3)       # u0, G0 = 1 + x + x² + x³
        b1, b2, b3 = bit, b1, b2
    return code_bits


def interleaver_permutation():
    """Return the interleaver permutation as a list mapping output index to input index.

    ``q(p)(k) = a(p)(t)`` with ``t = 15 - 4 * (k mod 4) - floor(k / 4)``
    ([802.15.4] 19.3.6), i.e. the symbol transmitted k-th is taken from
    position t.
    """
    return [15 - 4 * (k % 4) - k // 4 for k in range(INTERLEAVER_BLOCK_SYMBOLS)]


def interleave(code_bits):
    """Interleave code bits in blocks of 16 code symbols (32 bits)."""
    assert len(code_bits) % 32 == 0, "expected a whole number of interleaver blocks"
    permutation = interleaver_permutation()
    out = [0] * len(code_bits)
    for base in range(0, len(code_bits), 32):
        for k, t in enumerate(permutation):
            out[base + 2 * k] = code_bits[base + 2 * t]
            out[base + 2 * k + 1] = code_bits[base + 2 * t + 1]
    return out


def deinterleave(code_bits):
    """Undo `interleave` (the symbol received k-th belongs at position t)."""
    assert len(code_bits) % 32 == 0, "expected a whole number of interleaver blocks"
    permutation = interleaver_permutation()
    out = [0] * len(code_bits)
    for base in range(0, len(code_bits), 32):
        for k, t in enumerate(permutation):
            out[base + 2 * t] = code_bits[base + 2 * k]
            out[base + 2 * t + 1] = code_bits[base + 2 * k + 1]
    return out


def pad_bits(frame_length):
    """Return the number of padding bits following the tail bits.

    Tail and padding together occupy one whole octet when PHR + PSDU is an odd
    number of octets and two when it is even, which is the 5 or 13 bits of
    [802.15.4] 19.3.5.
    """
    octets = frame_length + PHR_OCTETS
    return 8 * (1 if octets % 2 else 2) - TAIL_BITS


def coded_length(frame_length):
    """Return the number of octets a coded frame occupies on air.

    `frame_length` is the PSDU length in octets, i.e. what the Frame Length
    field of a coded PHR carries — roughly half of what arrives.
    """
    octets = frame_length + PHR_OCTETS
    return (octets + (1 if octets % 2 else 2)) * 2


def phr_value(frame_length, whitened=True, fcs16=False):
    """Assemble a PHY header value from its fields ([802.15.4] Figure 19-4)."""
    assert 0 <= frame_length <= 0x7FF, "frame length out of range"
    return frame_length | (0x0800 if whitened else 0) | (0x1000 if fcs16 else 0)


def fcs(data, fcs16=False):
    """Return the frame check sequence for `data`, least significant octet first.

    FCS-32 is the ordinary Ethernet CRC-32; FCS-16 is ITU-T CRC-16 seeded with
    zeroes ([802.15.4] 7.2.10).
    """
    if fcs16:
        crc = 0
        for octet in data:
            crc ^= octet
            for _ in range(8):
                crc = (crc >> 1) ^ (0x8408 if crc & 1 else 0)
        return bytes([crc & 0xFF, (crc >> 8) & 0xFF])
    crc = 0xFFFFFFFF
    for octet in data:
        crc ^= octet
        for _ in range(8):
            crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
    crc ^= 0xFFFFFFFF
    return bytes([(crc >> (8 * i)) & 0xFF for i in range(4)])


def append_fcs(payload, fcs16=False):
    """Return `payload` with its frame check sequence appended, i.e. a complete PSDU."""
    return bytes(payload) + fcs(payload, fcs16=fcs16)


def encode_frame(psdu, whitened=True, fcs16=False, pad_value=1):
    """Build the coded part of a frame: everything on air except the SHR.

    Returns a bit list in transmission order, covering the encoded PHY header
    followed by the encoded, whitened PSDU. The steps are those of the
    reference modulator: concatenate PHR and PSDU, append tail and padding,
    convolutionally encode, interleave, then whiten the PSDU's code symbols
    only ([802.15.4] 19.3.2, 19.3.5, 19.3.6, 19.4).

    `pad_value` is the value of the padding bits following the 3 zero tail
    bits. Real transmitters have been seen to use both 0 and 1, and a decoder
    must not care, so it is a parameter here; see docs/sun-fsk-fec.md.
    """
    assert pad_value in (0, 1), "padding bits are 0 or 1"
    frame_length = len(psdu)
    phr = phr_value(frame_length, whitened=whitened, fcs16=fcs16)

    # PHR is transmitted most significant bit first, everything else least
    # significant bit first
    info_bits = bits_msb_first(phr, 16) + octets_to_bits(psdu)
    info_bits += [0] * TAIL_BITS + [pad_value] * pad_bits(frame_length)

    code_bits = interleave(convolutional_encode(info_bits))

    # whitening covers the PSDU's code symbols only: the encoded PHY header is
    # exactly the first interleaver block and is left alone
    if whitened:
        mask = pn9_sequence(len(code_bits) - 32)
        code_bits = code_bits[:32] + [bit ^ m for bit, m in zip(code_bits[32:], mask)]

    assert len(code_bits) == 8 * coded_length(frame_length), "coded length mismatch"
    return code_bits


def on_air_bits(psdu, whitened=True, fcs16=False, pad_value=1, preamble_octets=PREAMBLE_OCTETS):
    """Build a complete coded frame as it appears on air, SHR included.

    The SHR — preamble and SFD — is never coded, interleaved or whitened.
    """
    preamble = octets_to_bits([PREAMBLE_OCTET] * preamble_octets)
    sfd = bits_msb_first(SFD_CODED, 16)
    return preamble + sfd + encode_frame(psdu, whitened=whitened, fcs16=fcs16, pad_value=pad_value)
