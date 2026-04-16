#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

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
        self.assertEqual(tag_eob.offset, 9)
        self.assertAlmostEqual(float(str(tag_eob.value)), 0)


if __name__ == '__main__':
    gr_unittest.run(qa_gated_power_squelch_relative_cc)
