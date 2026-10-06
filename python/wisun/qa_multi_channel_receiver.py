#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for the multi-channel receiver's channelizer arithmetic.

What matters here is the rate the per-channel receivers end up working at. Without
oversampling it is channel spacing over symbol rate, which is 2 samples per symbol for
every Wi-SUN FSK mode - too few for the chain, measured against recordings - so the
oversampling has to reach them.
"""

from gnuradio import gr, gr_unittest  # noqa: F401

try:
    from gnuradio import wisun
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio import wisun

CHANNEL_SPACING = 200_000
SYMBOL_RATE = 100_000
CHANNELS = 8
SAMPLE_RATE = CHANNELS * CHANNEL_SPACING
CHANNEL_0 = 863_100_000


def build(oversampling, channels=(0, 1)):
    """Build a receiver for a few channels, centred so that channel 0 is on the grid."""
    return wisun.multi_channel_receiver(SAMPLE_RATE,
                                        CHANNEL_0 + 2 * CHANNEL_SPACING,
                                        CHANNEL_0,
                                        CHANNEL_SPACING,
                                        SYMBOL_RATE,
                                        list(channels),
                                        fec=True,
                                        oversampling=oversampling)


class qa_multi_channel_receiver(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def test_001_samples_per_symbol_without_oversampling(self):
        """Without oversampling the channel receivers get channel spacing over symbol rate."""
        receiver = build(oversampling=1)
        self.assertEqual(receiver.samples_per_symbol, CHANNEL_SPACING // SYMBOL_RATE)
        self.assertEqual(receiver.samples_per_symbol, 2)

    def test_002_oversampling_multiplies_samples_per_symbol(self):
        """Oversampling has to reach the channel receivers, which is the whole point of it."""
        for oversampling in (1, 2, 4):
            receiver = build(oversampling=oversampling)
            self.assertEqual(receiver.samples_per_symbol,
                             oversampling * CHANNEL_SPACING // SYMBOL_RATE)
            self.assertEqual(receiver.oversampling, oversampling)

    def test_003_the_default_oversamples(self):
        """The default must not leave the chain at 2 samples per symbol."""
        from gnuradio.wisun.multi_channel_receiver import DEFAULT_OVERSAMPLING
        receiver = build(oversampling=DEFAULT_OVERSAMPLING)
        self.assertGreater(receiver.samples_per_symbol, 2)

    def test_004_an_oversampling_the_channelizer_cannot_do_is_refused(self):
        """The channelizer accepts an oversampling of n_channels / i only."""
        with self.assertRaises(AssertionError):
            build(oversampling=3)  # 8 channels / 3 is not an integer


if __name__ == '__main__':
    gr_unittest.run(qa_multi_channel_receiver)
