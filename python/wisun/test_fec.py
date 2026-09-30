# coding: utf-8
#
# Copyright (c) 2026 Gardena GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pytest tests for the FEC reference encoder."""

import zlib

import pytest

from .fec import (SFD_CODED, append_fcs, bits_msb_first, bits_to_octets, coded_length, convolutional_encode,
                  deinterleave, encode_frame, fcs, interleave, interleaver_permutation, octets_to_bits, on_air_bits,
                  pad_bits, phr_value, pn9_sequence, value_msb_first)

# first 24 bits of the PN9 sequence given in [802.15.4] 16.2.3
PN9_EXAMPLE_DATA = [0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1]

# A real FEC-coded acknowledgement, captured at PhyModeID 0x13 on channel plan 33 and
# decoded with a Viterbi metric of zero. CODED_OCTETS is what was on air after the SFD,
# whitened and interleaved; PSDU is what it carries.
REAL_FRAME_CODED_OCTETS = bytes.fromhex(
    "c9c3dfce257701d78daa91c237bf1676a1412fc018208b0955decc7ca635db91700f26f20fff08f6"
    "a1db058452bc00f4d8835fffd51522e0c70186cdd7584b9677123d8087789944d970bf79e944c013"
    "b94e15250ccd78182640d968b1bce7e7ea896b8ede011aacd1435f48")
REAL_FRAME_PSDU = bytes.fromhex(
    "4aee870022fffeff5567440122fffeff5567440e082a09000507150a0500002000000215049474"
    "834432667dc4a4579eb1f6")
REAL_FRAME_PHR = 0x0832


def test_pn9_matches_the_standard():
    """PN9 must match the sequence printed in [802.15.4] 16.2.3."""
    assert pn9_sequence(len(PN9_EXAMPLE_DATA)) == PN9_EXAMPLE_DATA


def test_pn9_is_a_prefix_of_itself():
    """A shorter request must be a prefix of a longer one (the generator is seeded, not continued)."""
    assert pn9_sequence(100) == pn9_sequence(1000)[:100]


@pytest.mark.parametrize('frame_length,expected', [
    # worked values from docs/sun-fsk-fec.md; the first four are also the frame
    # sizes of the recorded PhyModeID 0x13 traffic
    (50, 108),
    (56, 120),
    (142, 292),
    (169, 344),
    (198, 404),
    (2047, 4100),
])
def test_coded_length(frame_length, expected):
    """The on-air length must follow the closed form for the padding."""
    assert coded_length(frame_length) == expected


@pytest.mark.parametrize('frame_length', range(1, 200))
def test_coded_length_is_a_whole_number_of_interleaver_blocks(frame_length):
    """Every coded frame must be a whole number of 4-octet interleaver blocks."""
    assert coded_length(frame_length) % 4 == 0
    # tail and padding together occupy one whole octet for an odd PHR + PSDU, two for an even one
    assert pad_bits(frame_length) in (5, 13)
    assert 8 * (frame_length + 2) + 3 + pad_bits(frame_length) == 4 * coded_length(frame_length)


def test_interleaver_permutation():
    """The permutation must be the one given in [802.15.4] 19.3.6."""
    assert interleaver_permutation() == [15, 11, 7, 3, 14, 10, 6, 2, 13, 9, 5, 1, 12, 8, 4, 0]


def test_interleaver_round_trip():
    """Deinterleaving must undo interleaving, and operate on whole code symbols."""
    code_bits = [(i * 7 + i // 3) % 2 for i in range(32 * 5)]
    assert deinterleave(interleave(code_bits)) == code_bits
    # symbols move as a unit: an interleaved block is a permutation of the symbol pairs
    symbols = [tuple(code_bits[i:i + 2]) for i in range(0, 32, 2)]
    interleaved = interleave(code_bits[:32])
    expected = [symbols[t] for t in interleaver_permutation()]
    assert [tuple(interleaved[i:i + 2]) for i in range(0, 32, 2)] == expected


def test_convolutional_encoder_complements_both_outputs():
    """An all-zero input must give all-one code bits, because both outputs are complemented."""
    assert convolutional_encode([0] * 10) == [1] * 20


def test_convolutional_encoder_first_symbols():
    """Hand-computed code symbols for a single one bit followed by zeros.

    With b(i) = 1 and the register empty: u1 = NOT(1) = 0, u0 = NOT(1) = 0. The
    one then walks through the three memory elements, complementing the outputs
    it appears in: u1 = 1 + x² + x³, u0 = 1 + x + x² + x³.
    """
    assert convolutional_encode([1, 0, 0, 0, 0]) == [0, 0,   # b(i)=1 in both taps
                                                     1, 0,   # b(i-1) in G0 only
                                                     0, 0,   # b(i-2) in both
                                                     0, 0,   # b(i-3) in both
                                                     1, 1]   # register empty again


def test_convolutional_encoder_is_rate_one_half():
    """Each input bit must produce exactly two code bits."""
    for length in (1, 7, 16, 100):
        assert len(convolutional_encode([1] * length)) == 2 * length


@pytest.mark.parametrize('frame_length,expected', [
    # reference values decoded off the air, from docs/sun-fsk-fec.md
    (142, 0x088E),
    (70, 0x0846),
])
def test_phr_value(frame_length, expected):
    """A whitened frame with a 4-octet FCS must give the documented PHR."""
    assert phr_value(frame_length, whitened=True, fcs16=False) == expected


def test_phr_bit_order_is_the_trap():
    """The PHY header is most significant bit first; reading it the other way corrupts it."""
    phr = 0x088E
    bits = bits_msb_first(phr, 16)
    assert value_msb_first(bits) == phr
    # reading the header's octets the way the PSDU's are read gives 0x1071 instead
    assert bits_to_octets(bits) == b'\x10\x71'


def test_psdu_bit_order_is_least_significant_first():
    """Everything except the PHY header is least significant bit first."""
    assert octets_to_bits(b'\x01') == [1, 0, 0, 0, 0, 0, 0, 0]
    assert bits_to_octets(octets_to_bits(b'\xde\xad\xbe\xef')) == b'\xde\xad\xbe\xef'


def test_fcs32_agrees_with_zlib():
    """FCS-32 is the ordinary Ethernet CRC-32, least significant octet first."""
    for payload in (b'', b'\x00', b'123456789', bytes(range(64))):
        assert fcs(payload) == zlib.crc32(payload).to_bytes(4, 'little')


def test_fcs16_known_value():
    """FCS-16 is ITU-T CRC-16 seeded with zeroes (the Kermit variant), LSB octet first."""
    assert fcs(b'123456789', fcs16=True) == (0x2189).to_bytes(2, 'little')


def test_append_fcs_produces_a_self_consistent_psdu():
    """A PSDU built by appending the FCS must verify against its own payload."""
    for fcs16 in (False, True):
        psdu = append_fcs(b'payload octets', fcs16=fcs16)
        width = 2 if fcs16 else 4
        assert fcs(psdu[:-width], fcs16=fcs16) == psdu[-width:]


@pytest.mark.parametrize('pad_value', [0, 1])
@pytest.mark.parametrize('frame_length', [5, 6, 50, 51, 142, 169])
def test_encoded_frame_has_the_expected_length(frame_length, pad_value):
    """Encoding must produce exactly coded_length() octets, whatever the padding."""
    psdu = bytes(range(frame_length % 256)) + bytes(frame_length - (frame_length % 256))
    psdu = psdu[:frame_length]
    code_bits = encode_frame(psdu, pad_value=pad_value)
    assert len(code_bits) == 8 * coded_length(frame_length)


def test_whitening_leaves_the_encoded_header_alone():
    """Whitening must cover the PSDU's code symbols only, not the encoded PHY header.

    The comparison is against the same frame encoded but not whitened, built here
    rather than with `whitened=False` — that flag also clears the PHR's whitening
    bit, which would change the encoded header for a second reason.
    """
    psdu = append_fcs(b'some payload')
    info_bits = (bits_msb_first(phr_value(len(psdu), whitened=True), 16) + octets_to_bits(psdu)
                 + [0] * 3 + [1] * pad_bits(len(psdu)))
    plain = interleave(convolutional_encode(info_bits))
    whitened = encode_frame(psdu, whitened=True)
    assert whitened[:32] == plain[:32], "the first interleaver block must not be whitened"
    assert whitened[32:] != plain[32:]
    mask = pn9_sequence(len(plain) - 32)
    assert whitened[32:] == [bit ^ m for bit, m in zip(plain[32:], mask)]


def test_real_frame_is_reproduced_bit_exactly():
    """The reference encoder must reproduce a real captured frame, octet for octet.

    This is the check that is worth more than all the synthetic vectors together:
    a wrong interleaver, trellis, whitening phase, bit order or padding value does
    not reproduce real traffic.
    """
    code_bits = encode_frame(REAL_FRAME_PSDU, whitened=True, fcs16=False, pad_value=1)
    assert bits_to_octets(code_bits) == REAL_FRAME_CODED_OCTETS


def test_real_frame_phr_and_fcs():
    """The captured frame's PHR and FCS must be what the encoder and CRC say they are."""
    assert phr_value(len(REAL_FRAME_PSDU), whitened=True, fcs16=False) == REAL_FRAME_PHR
    assert len(REAL_FRAME_PSDU) == REAL_FRAME_PHR & 0x07FF
    assert fcs(REAL_FRAME_PSDU[:-4]) == REAL_FRAME_PSDU[-4:]
    assert len(REAL_FRAME_CODED_OCTETS) == coded_length(len(REAL_FRAME_PSDU))


def test_padding_value_only_affects_the_last_block():
    """The padding sits at the end, so only the final interleaver block can differ."""
    psdu = append_fcs(b'payload')
    zeros = encode_frame(psdu, pad_value=0)
    ones = encode_frame(psdu, pad_value=1)
    assert zeros[:-32] == ones[:-32]
    assert zeros[-32:] != ones[-32:]


def test_on_air_bits_starts_with_preamble_and_coded_sfd():
    """The SHR is never coded, interleaved or whitened."""
    psdu = append_fcs(b'payload')
    bits = on_air_bits(psdu, preamble_octets=8)
    # the preamble runs 0101... and ends on a 1, immediately before the SFD
    assert bits[:64] == [0, 1] * 32
    assert value_msb_first(bits[64:80]) == SFD_CODED
    assert bits[80:] == encode_frame(psdu)
