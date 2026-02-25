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
    from gnuradio.wisun import correlate_sync_word_bb
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import correlate_sync_word_bb

SFD = 0b1001_0000_0100_1110


def make_tag(key, value, offset, srcid=None):
    """Create a tag."""
    tag = gr.tag_t()
    tag.key = pmt.string_to_symbol(key)
    tag.value = pmt.to_pmt(value)
    tag.offset = offset
    if srcid is not None:
        tag.srcid = pmt.to_pmt(srcid)
    return tag


class qa_correlate_sync_word_bb(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def test_001_correlate_sync_word_bb(self):
        """Test basic block operation."""
        src_data = [
            0, 1, 0, 1, 0, 1, 0, 1,  # preamble
            0, 1, 0, 1, 0, 1, 0, 1,  # preamble
            0, 1, 0, 1, 0, 1, 0, 1,  # preamble
            0, 1, 0, 1, 0, 1, 0, 1,  # preamble
            1, 0, 0, 1, 0, 0, 0, 0,  # SFD
            0, 1, 0, 0, 1, 1, 1, 0,  # SFD
            0, 0, 0, 0, 0, 0, 0, 0,  # PHR
            0, 0, 0, 1, 0, 0, 0, 0,  # PHR
            1, 1, 0, 0, 0, 0, 0, 0,  # payload data ..
            1, 1, 0, 0, 0, 0, 0, 1,  # payload data ..
            1, 1, 0, 0, 0, 0, 1, 0,  # payload data ..
            1, 1, 0, 0, 0, 0, 1, 1,  # payload data ..
            1, 1, 0, 0, 0, 1, 0, 0,  # payload data ..
            1, 1, 0, 0, 0, 1, 0, 1,  # payload data ..
            1, 1, 0, 0, 0, 1, 1, 0,  # payload data ..
            1, 1, 0, 0, 0, 1, 1, 1,  # payload data ..
            1, 1, 0, 0, 0, 0, 0, 0,  # payload data ..
            1, 1, 0, 0, 0, 0, 0, 1,  # payload data ..
            1, 1, 0, 0, 0, 0, 1, 0,  # payload data ..
            1, 1, 0, 0, 0, 0, 1, 1,  # payload data ..
            1, 1, 0, 0, 0, 1, 0, 0,  # payload data ..
            1, 1, 0, 0, 0, 1, 0, 1,  # payload data ..
            1, 1, 0, 0, 0, 1, 1, 0,  # payload data ..
            1, 1, 0, 0, 0, 1, 1, 1,  # payload data ..
        ]

        # set up fg
        src = blocks.vector_source_b(src_data)
        blk = correlate_sync_word_bb(SFD)
        dst = blocks.vector_sink_b()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        # check data
        #
        # note: the actual data is unchanged, but
        # - we have a history of 33 (SFD bits + PHR bits + 1)
        # - this leads to a delay of 32 samples, which manifests as initial zeros
        result_data = dst.data()
        self.assertEqual(len(result_data), len(src_data))
        self.assertEqual(result_data[0:32], [0] * 32)
        self.assertEqual(result_data[32:], src_data[:-32])
        # check tags
        self.assertEqual(len(dst.tags()), 10)
        tags = dst.tags()
        tag_keys = set([str(tag.key) for tag in tags])
        assert tag_keys == set(("wisun-packet",
                                "wisun-preamble-length",
                                "wisun-packet-sfd",
                                "wisun-packet-phr",
                                "wisun-packet-phr-mode-switch",
                                "wisun-packet-phr-fcs-type",
                                "wisun-packet-phr-data-whitening",
                                "wisun-packet-phr-frame-length",
                                "wisun-packet-payload",
                                "wisun-packet-end"))
        # check packet tag
        tag = [tag for tag in tags if str(tag.key) == "wisun-packet"][0]
        self.assertEqual(str(tag.key), "wisun-packet")
        self.assertEqual(int(str(tag.value)), 16)
        self.assertEqual(tag.offset, 64)  # 32 zeroes (from history) + 32 preamble bits

    def test_002_correlate_sync_word_bb(self):
        """Test to make sure other tags are not affected."""
        src_data = [
            0, 0, 0, 0, 0, 0, 0, 0,
            1, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
        ]

        # set up fg
        src = blocks.vector_source_b(src_data, tags=(make_tag("test", 42, 8),))
        blk = correlate_sync_word_bb(SFD)
        dst = blocks.vector_sink_b()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()
        result_data = dst.data()
        self.assertEqual(len(result_data), len(src_data))
        self.assertEqual(result_data[0:32], [0] * 32)
        self.assertEqual(result_data[32:], src_data[:-32])
        # check tag
        self.assertEqual(len(dst.tags()), 1)
        tag = dst.tags()[0]
        self.assertEqual(str(tag.key), "test")
        self.assertEqual(int(str(tag.value)), 42)
        # tag is delayed by 32 samples due to history, i.e. it is still on "1"
        self.assertEqual(tag.offset, 40)
        self.assertEqual(result_data[40], 1)


if __name__ == '__main__':
    gr_unittest.run(qa_correlate_sync_word_bb)
