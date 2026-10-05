#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Acquisition tests for the whole baseband chain, driven by modulated samples.

Unlike qa_uncoded_receive.py, which starts at the bit level, this feeds complex samples
through squelch, DC correction, AGC and symbol synchronization, so it covers what the
receiver has to get done inside the preamble before the sync word arrives.

The frames carry a carrier offset larger than the frequency deviation, which puts the
whole discriminator output on one side of zero. Until the DC estimate is applied the
slicer therefore reads a constant, and those symbols are lost to the sync word
correlator - which is what makes the length of the estimation window a limit on how
short a preamble the receiver can still acquire.
"""

import numpy as np
import pmt
from gnuradio import blocks, gr, gr_unittest

try:
    from gnuradio import wisun
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio import wisun
from gnuradio.wisun import fec
from gnuradio.wisun.parameters import SUN_FSK_SFD_UNCODED

# the lowest samples per symbol the receiver is used at, and the hardest to acquire in
SAMPLES_PER_SYMBOL = 5
# modulation index 0.5, i.e. a deviation of a quarter of the symbol rate, in rad/sample
DEVIATION = 2 * np.pi / (4 * SAMPLES_PER_SYMBOL)
# a carrier offset beyond the deviation: both symbols land on the same side of zero
CARRIER_OFFSET = 1.3 * DEVIATION
NOISE_AMPLITUDE = 0.01  # the level the squelch tracks as its noise floor
NOISE_SAMPLES = 4000


def frame_bits(psdu, preamble_octets):
    """Build an uncoded frame as it appears on air, with a preamble of the given length."""
    preamble = fec.octets_to_bits([fec.PREAMBLE_OCTET] * preamble_octets)
    sfd = fec.bits_msb_first(SUN_FSK_SFD_UNCODED, 16)
    phr = fec.bits_msb_first(fec.phr_value(len(psdu), whitened=True), 16)
    psdu_bits = fec.octets_to_bits(psdu)
    mask = fec.pn9_sequence(len(psdu_bits))
    return preamble + sfd + phr + [bit ^ m for bit, m in zip(psdu_bits, mask, strict=True)]


def modulate(bits, carrier_offset=CARRIER_OFFSET, seed=1):
    """Modulate bits as 2-FSK, framed by noise so the squelch sees a burst."""
    rng = np.random.default_rng(seed)
    symbols = np.repeat([DEVIATION if bit else -DEVIATION for bit in bits], SAMPLES_PER_SYMBOL)
    burst = np.exp(1j * np.cumsum(symbols + carrier_offset)).astype(np.complex64)

    def noise():
        return (rng.normal(0, NOISE_AMPLITUDE, NOISE_SAMPLES)
                + 1j * rng.normal(0, NOISE_AMPLITUDE, NOISE_SAMPLES)).astype(np.complex64)

    return np.concatenate([noise(), burst, noise()])


class baseband_receiver(gr.top_block):
    """The whole baseband receive chain, fed from a vector of samples."""

    def __init__(self, samples):
        """Build the flow graph."""
        gr.top_block.__init__(self, "baseband_receiver")
        self.source = blocks.vector_source_c(samples.tolist())
        self.receiver = wisun.baseband_channel_receiver(SAMPLES_PER_SYMBOL)
        self.sink = blocks.message_debug()

        self.connect(self.source, self.receiver)
        self.msg_connect((self.receiver, 'pdus'), (self.sink, 'store'))

    def packets(self):
        """Return the payload of every received packet."""
        return [bytes(pmt.u8vector_elements(pmt.cdr(self.sink.get_message(i))))
                for i in range(self.sink.num_messages())]

    def metadata(self, index, key):
        """Return a metadata value of the packet with the given index."""
        entry = pmt.dict_ref(pmt.car(self.sink.get_message(index)), pmt.string_to_symbol(key), pmt.PMT_NIL)
        return None if pmt.is_null(entry) else pmt.to_python(entry)


class qa_baseband_acquisition(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def receive(self, payload, preamble_octets, carrier_offset=CARRIER_OFFSET):
        """Run a single frame through the chain and return it for inspection."""
        bits = frame_bits(fec.append_fcs(payload), preamble_octets)
        tb = baseband_receiver(modulate(bits, carrier_offset))
        tb.run()
        return tb

    def test_001_a_frame_with_a_five_octet_preamble_is_acquired(self):
        """40 preamble symbols must be enough to acquire a frame carrying a carrier offset.

        The estimation window takes the first symbols of the burst, and the correlator
        needs 16 alternating symbols plus the 16 sync word symbols after that, so a
        window of 30 symbols leaves this frame undetectable while 20 does not.
        """
        payload = bytes(range(40))
        tb = self.receive(payload, preamble_octets=5)

        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][4:], payload)
        self.assertTrue(tb.metadata(0, 'wisun-fcs-valid'))

    def test_002_the_estimation_window_leaves_most_of_the_preamble(self):
        """A standard preamble must still be mostly usable once the estimate is applied.

        The run the correlator measures is what is left of the preamble after the window,
        so it puts a number on the margin the receiver acquires with: 45 of the 64 symbols
        here, against 35 with an estimation window of 30 symbols.
        """
        tb = self.receive(bytes(range(40)), preamble_octets=8)

        self.assertEqual(len(tb.packets()), 1)
        self.assertGreaterEqual(tb.metadata(0, 'wisun-preamble-length'), 40)

    def test_003_a_short_preamble_without_a_carrier_offset(self):
        """Without an offset the uncorrected symbols still slice correctly.

        The control for the two tests above: it is the offset, not the preamble length on
        its own, that makes the estimation window cost symbols.
        """
        payload = bytes(range(40))
        tb = self.receive(payload, preamble_octets=4, carrier_offset=0.0)

        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][4:], payload)


if __name__ == '__main__':
    gr_unittest.run(qa_baseband_acquisition)
