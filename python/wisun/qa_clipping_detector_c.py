#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for the clipping_detector_c block.

What matters is that a clipping input is noticed at all: too much gain does not only cost
packets, it produces copies of frames on channels they were never sent on, and those copies
are indistinguishable from real ones once a capture has been written.
"""

from gnuradio import blocks, gr, gr_unittest

try:
    from gnuradio.wisun import clipping_detector_c
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import clipping_detector_c


class qa_clipping_detector_c(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def count(self, samples, threshold=0.99):
        """Run samples through the detector and return it for inspection."""
        detector = clipping_detector_c(threshold, 1000)
        self.tb.connect(blocks.vector_source_c(samples), detector)
        self.tb.run()
        return detector

    def test_001_a_clean_signal_is_not_clipping(self):
        """Half-scale samples must not count, however many there are."""
        detector = self.count([complex(0.5, -0.5)] * 4096)

        self.assertEqual(detector.samples(), 4096)
        self.assertEqual(detector.clipped_samples(), 0)

    def test_002_full_scale_samples_are_counted(self):
        """A sample at full scale counts, whichever component reaches it."""
        samples = [complex(0.1, 0.1)] * 100
        samples[10] = complex(1.0, 0.0)    # in phase
        samples[20] = complex(0.0, -1.0)   # in quadrature
        samples[30] = complex(-0.995, 0.2)  # just over the threshold
        detector = self.count(samples)

        self.assertEqual(detector.samples(), 100)
        self.assertEqual(detector.clipped_samples(), 3)

    def test_003_the_threshold_is_honoured(self):
        """A lower threshold must count samples a higher one lets pass."""
        samples = [complex(0.8, 0.0)] * 64

        self.assertEqual(self.count(samples, threshold=0.99).clipped_samples(), 0)
        self.setUp()
        self.assertEqual(self.count(samples, threshold=0.7).clipped_samples(), 64)

    def test_004_counts_survive_many_reporting_periods(self):
        """The running totals must not be reset by the periodic reports."""
        samples = ([complex(1.0, 1.0)] + [complex(0.2, 0.2)] * 9) * 1000
        detector = self.count(samples)

        self.assertEqual(detector.samples(), 10000)
        self.assertEqual(detector.clipped_samples(), 1000)


if __name__ == '__main__':
    gr_unittest.run(qa_clipping_detector_c)
