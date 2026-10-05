#!/usr/bin/env python

# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for correlate_sync_word_bb block."""

import pmt
from gnuradio import blocks, gr, gr_unittest

try:
    from gnuradio.wisun import correlate_sync_word_bb
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import correlate_sync_word_bb
from gnuradio.wisun import fec

SFD = 0b1001_0000_0100_1110
SFD_CODED = 0b0110_1111_0100_1110


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
            0, 0, 0, 0, 0, 0, 0, 0,  # PHR: frame length 12 (PSDU octets alone,
            0, 0, 0, 0, 1, 1, 0, 0,  # PHR  the SFD+PHR octets below add up to 16)
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
        tag_keys = {str(tag.key) for tag in tags}
        assert tag_keys == {"wisun-packet",
                                "wisun-preamble-length",
                                "wisun-packet-sfd",
                                "wisun-packet-phr",
                                "wisun-packet-phr-mode-switch",
                                "wisun-packet-phr-fcs-type",
                                "wisun-packet-phr-data-whitening",
                                "wisun-packet-phr-frame-length",
                                "wisun-packet-payload",
                                "wisun-packet-end"}
        # check packet tag
        tag = next(tag for tag in tags if str(tag.key) == "wisun-packet")
        self.assertEqual(str(tag.key), "wisun-packet")
        # PHR frame length (12) is the PSDU alone; the SFD and PHR octets (4) are
        # added back in, since framing spans the whole frame from the tag's offset
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

    def test_003_correlate_sync_word_bb_fec(self):
        """Test detection of a FEC-coded frame, whose PHY header has to be decoded."""
        # a 142-octet PSDU, whitened, with a 4-octet FCS: PHR 0x088e
        psdu = fec.append_fcs(bytes(range(138)))
        self.assertEqual(len(psdu), 142)
        preamble_octets = 8
        src_data = fec.on_air_bits(psdu, preamble_octets=preamble_octets)

        # set up fg
        src = blocks.vector_source_b(src_data)
        blk = correlate_sync_word_bb(SFD_CODED, True)
        dst = blocks.vector_sink_b()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()

        tags = {str(tag.key): tag for tag in dst.tags()}
        # the PHY header must come out of the first interleaver block
        self.assertEqual(int(str(tags["wisun-packet-phr"].value)), 0x088E)
        self.assertEqual(int(str(tags["wisun-packet-phr-frame-length"].value)), 142)
        self.assertEqual(int(str(tags["wisun-packet-phr-fcs-type"].value)), 0)
        self.assertEqual(int(str(tags["wisun-packet-phr-data-whitening"].value)), 1)
        # framing must be driven by the on-air length, not by the frame length
        self.assertEqual(int(str(tags["wisun-packet"].value)), 2 + fec.coded_length(142))
        self.assertEqual(int(str(tags["wisun-packet-sfd"].value)), SFD_CODED)
        # the packet tag sits on the first bit of the SFD, delayed by the block's history
        delay = 16 + 32
        self.assertEqual(tags["wisun-packet"].offset, delay + 8 * preamble_octets)

    def test_004_uncoded_packet_length_spans_the_whole_frame(self):
        """The length tag must cover the SFD and PHY header, not only the PSDU.

        The frame length field counts PSDU octets alone, so framing the span from the SFD
        by that number cuts the frame short by exactly the 4 SFD and PHY header octets.
        With a 4-octet frame check sequence that happens to cost only the FCS; with a
        2-octet one it eats into the payload.
        """
        for fcs16 in (False, True):
            psdu = fec.append_fcs(bytes(range(20)), fcs16=fcs16)
            phr = fec.phr_value(len(psdu), whitened=False, fcs16=fcs16)
            bits = (fec.octets_to_bits([fec.PREAMBLE_OCTET] * 8)
                    + fec.bits_msb_first(SFD, 16)
                    + fec.bits_msb_first(phr, 16)
                    + fec.octets_to_bits(psdu))

            src = blocks.vector_source_b(bits + [0] * 64)
            blk = correlate_sync_word_bb(SFD)
            dst = blocks.vector_sink_b()
            self.tb.connect(src, blk, dst)
            self.tb.run()

            tag = next(t for t in dst.tags() if str(t.key) == "wisun-packet")
            self.assertEqual(int(str(tag.value)), 4 + len(psdu))
            self.setUp()

    def test_005_a_short_preamble_is_still_detected(self):
        """A frame whose preamble is shorter than the detector's taste must still be found.

        The preamble may legitimately be as short as 8 symbols, and a receiver asking for
        more than it carries never sees such a frame however strong it is. One recording's
        169-octet frame is exactly this case.
        """
        psdu = fec.append_fcs(bytes(range(46)))
        bits = fec.on_air_bits(psdu, preamble_octets=2)  # 16 preamble bits

        src = blocks.vector_source_b(bits + [0] * 64)
        blk = correlate_sync_word_bb(SFD_CODED, True)
        dst = blocks.vector_sink_b()
        self.tb.connect(src, blk, dst)
        self.tb.run()

        tag = next((t for t in dst.tags() if str(t.key) == "wisun-packet"), None)
        self.assertIsNotNone(tag, "frame with a 16-bit preamble was not detected")
        self.assertEqual(int(str(tag.value)), 2 + fec.coded_length(len(psdu)))

    def test_006_correlate_sync_word_bb_fec_is_deaf_to_uncoded_sfd(self):
        """A receiver locked to one SFD must be deaf to the other."""
        psdu = fec.append_fcs(bytes(range(46)))
        src_data = fec.on_air_bits(psdu)

        src = blocks.vector_source_b(src_data)
        blk = correlate_sync_word_bb(SFD, True)  # uncoded SFD, coded frames
        dst = blocks.vector_sink_b()
        self.tb.connect(src, blk)
        self.tb.connect(blk, dst)
        self.tb.run()

        self.assertEqual(len(dst.tags()), 0)


if __name__ == '__main__':
    gr_unittest.run(qa_correlate_sync_word_bb)
