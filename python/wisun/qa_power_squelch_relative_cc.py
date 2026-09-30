#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for power_squelch_relative_cc block."""

from gnuradio import blocks, gr, gr_unittest

try:
    from gnuradio.wisun import power_squelch_relative_cc
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import power_squelch_relative_cc


class qa_power_squelch_relative_cc(gr_unittest.TestCase):
    """Unit tests for power_squelch_relative_cc block."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def test_001_basic(self):
        """Test basic block function."""
        src_data = (
            1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9
        )

        expected_result = (
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1e-9, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        )

        # set up fg
        src = blocks.vector_source_c(src_data)
        blk = power_squelch_relative_cc(30, 1)
        dst = blocks.vector_sink_c()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        result_data = dst.data()
        self.assertEqual(len(src_data), len(result_data))
        self.assertComplexTuplesAlmostEqual(result_data, expected_result, places=10)
        # check tags
        self.assertEqual(len(dst.tags()), 2)
        tags = dst.tags()
        tag_sob = tags[0]
        self.assertEqual(str(tag_sob.key), "squelch_sob")
        self.assertEqual(tag_sob.offset, 11)
        self.assertAlmostEqual(float(str(tag_sob.value)), 1)
        tag_eob = tags[1]
        self.assertEqual(str(tag_eob.key), "squelch_eob")
        self.assertEqual(tag_eob.offset, 20)
        self.assertAlmostEqual(float(str(tag_eob.value)), 0)

    def test_002_squelch_closes_again_after_the_noise_floor_rises(self):
        """A risen noise floor must be picked up, so that the squelch closes again.

        The noise floor used to be the lowest power seen since the flow graph started, which
        can never recover from a reading that is too low: once the real noise rises above the
        threshold derived from it, the squelch stays open for the rest of the run. That costs
        more than the squelch itself, because tag_based_dc_correction_ff re-estimates only
        when a burst tag arrives, and an open squelch stops producing them.
        """
        # a brief very quiet stretch sets a low floor, then the noise floor rises by 60 dB
        # and stays there; nothing here is a burst, so the squelch has no business being open
        quiet = [1e-9] * 100
        risen = [1e-6] * 30000
        src = blocks.vector_source_c(tuple(quiet + risen))
        blk = power_squelch_relative_cc(30, 1)
        dst = blocks.vector_sink_c()
        self.tb.connect(src, blk, dst)
        self.tb.run()

        keys = [str(tag.key) for tag in dst.tags()]
        self.assertEqual(keys.count("squelch_sob"), 1, "the risen noise should open it once")
        self.assertEqual(keys.count("squelch_eob"), 1, "and it must then close again")
        # once closed it must stay closed, so the tail of the output is muted
        self.assertEqual(dst.data()[-1], 0)


if __name__ == '__main__':
    gr_unittest.run(qa_power_squelch_relative_cc)
