#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import math

from gnuradio import gr, gr_unittest
from gnuradio import blocks
try:
    from gnuradio.wisun import rssi_tag_cc
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import rssi_tag_cc


class qa_rssi_tag_cc(gr_unittest.TestCase):
    """Unit tests for the rssi_tag_cc block."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def test_001_test_data_unmodified(self):
        """Test to assert that data is not modified."""
        src_data = (
            1, 2, 3, 4, 5, 6, 7, 8,
            1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8,
            1.1 + 1.2j, 1.3 - 1.4j, -1.5 + 1.6j, -1.7 - 1.8j
        )

        # set up fg
        src = blocks.vector_source_c(src_data)
        blk = rssi_tag_cc(100)
        dst = blocks.vector_sink_c()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        result_data = dst.data()
        self.assertEqual(len(src_data), len(result_data))
        self.assertComplexTuplesAlmostEqual(src_data, result_data)

    def test_002_test_rssi_tags(self):
        """Test to assert correct generation of RSSI tags."""
        src_data = (
            2, 2, 2, 2,
            1, 2, 3, 4,
            -1, -1, -1, -1,
            1.1 + 1.2j, 1.2 - 1.3j, 1.3 + 1.4j, 1.4 - 1.5j
        )

        # set up fg
        src = blocks.vector_source_c(src_data)
        blk = rssi_tag_cc(4)
        dst = blocks.vector_sink_c()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        result_data = dst.data()
        self.assertEqual(len(src_data), len(result_data))
        self.assertComplexTuplesAlmostEqual(src_data, result_data)
        # check tags
        self.assertEqual(len(dst.tags()), 4)
        tags = dst.tags()
        for tag in tags:
            self.assertEqual(str(tag.key), "rssi")
        self.assertEqual(tags[0].offset, 3)
        self.assertAlmostEqual(float(str(tags[0].value)), 10 * math.log10(4), 5)
        self.assertEqual(tags[1].offset, 7)
        self.assertAlmostEqual(float(str(tags[1].value)), 10 * math.log10(7.5), 5)
        self.assertEqual(tags[2].offset, 11)
        self.assertAlmostEqual(float(str(tags[2].value)), 0)
        self.assertEqual(tags[3].offset, 15)
        self.assertAlmostEqual(float(str(tags[3].value)),
                               10 * math.log10((abs(1.1 + 1.2j)**2 + abs(1.2 - 1.3j)**2 +
                                                abs(1.3 + 1.4j)**2 + abs(1.4 - 1.5j)**2) / 4),
                               5)


if __name__ == '__main__':
    gr_unittest.run(qa_rssi_tag_cc)
