#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import cmath

from gnuradio import gr, gr_unittest
from gnuradio import blocks
try:
    from gnuradio.wisun import gated_power_squelch_relative_cc
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import gated_power_squelch_relative_cc


class qa_gated_power_squelch_relative_cc(gr_unittest.TestCase):
    """Unit tests for gated_power_squelch_relative_cc block."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def test_001_basic(self):
        """Test basic block funciton."""
        src_data = (
            1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9, 1e-9
        )

        expected_result = (
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            0, 0, 0
        )

        # set up fg
        src = blocks.vector_source_c(src_data)
        blk = gated_power_squelch_relative_cc(30, 1, 3)
        dst = blocks.vector_sink_c()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        result_data = dst.data()
        self.assertEqual(len(result_data), len(expected_result))
        self.assertComplexTuplesAlmostEqual(result_data, expected_result, places=10)
        # check tags
        self.assertEqual(len(dst.tags()), 2)
        tags = dst.tags()
        tag_sob = tags[0]
        self.assertEqual(str(tag_sob.key), "squelch_sob")
        self.assertEqual(tag_sob.offset, 0)
        self.assertAlmostEqual(float(str(tag_sob.value)), 1)
        tag_eob = tags[1]
        self.assertEqual(str(tag_eob.key), "squelch_eob")
        # the first item that is no longer signal, i.e. the first trailing zero; this is
        # the counterpart of squelch_sob naming the first item that is signal
        self.assertEqual(tag_eob.offset, 10)
        self.assertAlmostEqual(float(str(tag_eob.value)), 0)

    def test_002_output_is_correct_when_output_space_is_the_limit(self):
        """A long open burst must pass through intact however little output space there is.

        The scheduler hands over every input item available and bounds only noutput_items,
        so an open squelch routinely has far more to pass on than there is room for. The
        block used to write all of it regardless, running past the end of the output buffer
        by a factor of a hundred or more; keeping to the buffer means the input it did not
        get to must stay unconsumed, or samples go missing instead.
        """
        n_quiet = 2000
        n_signal = 6000
        # A burst of constant magnitude, so the squelch opens and closes cleanly, but with
        # every sample a different value, so that a duplicated or dropped stretch cannot
        # hide behind a constant.
        burst = [cmath.exp(1j * i) for i in range(n_signal)]
        src_data = tuple([1e-9] * n_quiet + burst)
        src = blocks.vector_source_c(src_data)
        blk = gated_power_squelch_relative_cc(30, 1, 3)
        dst = blocks.vector_sink_c()
        self.tb.connect(src, blk, dst)
        # only this block is throttled, so its input piles up far beyond its output space
        blk.set_max_noutput_items(16)
        self.tb.run()

        # the whole burst, in order, exactly once, and nothing from the quiet stretch
        result = dst.data()
        self.assertEqual(len(result), n_signal)
        self.assertComplexTuplesAlmostEqual(result, tuple(burst), places=6)


if __name__ == '__main__':
    gr_unittest.run(qa_gated_power_squelch_relative_cc)
