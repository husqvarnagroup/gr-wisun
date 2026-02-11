#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest
from gnuradio import blocks
import pmt
try:
    from gnuradio.wisun import packet_data_gate_bb
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import packet_data_gate_bb


def make_tag(key, value, offset, srcid=None):
    """Create a tag."""
    tag = gr.tag_t()
    tag.key = pmt.string_to_symbol(key)
    tag.value = pmt.to_pmt(value)
    tag.offset = offset
    if srcid is not None:
        tag.srcid = pmt.to_pmt(srcid)
    return tag


class qa_packet_data_gate_bb(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def test_001_no_tag_no_data(self):
        """Test to ensure that non-packet data is not passed."""
        src_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        # set up fg
        src = blocks.vector_source_b(src_data)
        blk = packet_data_gate_bb("wisun-packet")
        dst = blocks.vector_sink_b()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        self.assertEqual(len(dst.data()), 0)

    def test_002_one_packet_and_tags(self):
        """Test correct gating of one packet."""
        src_data = [
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
        ]
        expected_result = [
            2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7,
            8, 9, 0, 1, 2, 3, 4, 5
        ]
        # set up fg
        src = blocks.vector_source_b(src_data,
                                     tags=(
                                         make_tag("wisun-packet", 3, 2),
                                         make_tag("test", 123, 3),
                                         make_tag("test2", 321, 1)
                                     ))
        blk = packet_data_gate_bb("wisun-packet")
        dst = blocks.vector_sink_b()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        result_data = dst.data()
        self.assertEqual(len(result_data), 3 * 8)
        self.assertEqual(result_data, expected_result)
        # check tags
        self.assertEqual(len(dst.tags()), 2)
        length_tag = dst.tags()[0]
        self.assertEqual(str(length_tag.key), "wisun-packet")
        self.assertEqual(length_tag.offset, 0)
        self.assertEqual(int(str(length_tag.value)), 3)
        test_tag = dst.tags()[1]
        self.assertEqual(str(test_tag.key), "test")
        self.assertEqual(test_tag.offset, 1)
        self.assertEqual(int(str(test_tag.value)), 123)

    def test_003_two_packets(self):
        """Test correct gating of two packets."""
        src_data = [
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
        ]
        expected_result = [
            2, 3, 4, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4, 5, 6, 7,
            0, 1, 2, 3, 4, 5, 6, 7
        ]
        # set up fg
        src = blocks.vector_source_b(src_data,
                                     tags=(
                                         make_tag("wisun-packet", 2, 2),
                                         make_tag("wisun-packet", 1, 30)
                                     ))
        blk = packet_data_gate_bb("wisun-packet")
        dst = blocks.vector_sink_b()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        result_data = dst.data()
        self.assertEqual(len(result_data), 24)
        self.assertEqual(result_data, expected_result)
        # check tags
        self.assertEqual(len(dst.tags()), 2)
        tag1 = dst.tags()[0]
        self.assertEqual(str(tag1.key), "wisun-packet")
        self.assertEqual(tag1.offset, 0)
        self.assertEqual(int(str(tag1.value)), 2)
        tag2 = dst.tags()[1]
        self.assertEqual(str(tag2.key), "wisun-packet")
        self.assertEqual(tag2.offset, 16)
        self.assertEqual(int(str(tag2.value)), 1)


if __name__ == '__main__':
    gr_unittest.run(qa_packet_data_gate_bb)
