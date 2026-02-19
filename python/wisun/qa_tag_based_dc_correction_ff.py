#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for tag_based_dc_correction_ff block."""

from gnuradio import gr, gr_unittest
from gnuradio import blocks
import pmt
try:
    from gnuradio.wisun import tag_based_dc_correction_ff
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import tag_based_dc_correction_ff


def make_tag(key, value, offset, srcid=None):
    """Create a tag."""
    tag = gr.tag_t()
    tag.key = pmt.string_to_symbol(key)
    tag.value = pmt.to_pmt(value)
    tag.offset = offset
    if srcid is not None:
        tag.srcid = pmt.to_pmt(srcid)
    return tag


class qa_tag_based_dc_correction_ff(gr_unittest.TestCase):
    """Tests for tag based DC offset correction block."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def test_001_tag_based_dc_correction(self):
        """Test with two signal bursts."""
        src_data = tuple(
            10 * [100] +
            5 * [7, 9] +
            10 * [-100] +
            5 * [-1.5, 0.5] +
            [0]
        )

        expected_result = (
            10 * [100] +
            2 * [7, 9] +
            3 * [-1, 1] +
            10 * [-100] +
            2 * [-1.5, 0.5] +
            3 * [-1, 1] +
            [0]
        )

        # set up fg
        src = blocks.vector_source_f(src_data,
                                     tags=(make_tag("sob", 0, 10),
                                           make_tag("eob", 0, 20),
                                           make_tag("sob", 0, 30),
                                           make_tag("eob", 0, 40)))
        blk = tag_based_dc_correction_ff("sob", "eob", 4)
        dst = blocks.vector_sink_f()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        result_data = dst.data()
        self.assertEqual(len(result_data), len(expected_result))
        self.assertFloatTuplesAlmostEqual(result_data, expected_result)
        # check tags
        self.assertEqual(len(dst.tags()), 6)
        tags = dst.tags()
        # for tag in tags:
        #     print(f"tag {tag.key} for sample {tag.offset}: {tag.value}")
        corr_start_tags = [t for t in tags if str(t.key) == "dc_correction_correction_start"]
        assert len(corr_start_tags) == 2
        assert corr_start_tags[0].offset == 14
        assert pmt.to_float(corr_start_tags[0].value) == 8
        assert corr_start_tags[1].offset == 34
        assert pmt.to_float(corr_start_tags[1].value) == -0.5


if __name__ == '__main__':
    gr_unittest.run(qa_tag_based_dc_correction_ff)
