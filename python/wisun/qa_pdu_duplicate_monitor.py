#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for the pdu_duplicate_monitor block.

The case it is for: a transmitter with a spurious sideband puts a copy of its frame on
another channel, and the receiver listening there decodes it as a frame of its own. A
corrupted copy fails its frame check sequence, but a bit-exact one does not, and nothing
else notices it.

A retransmission repeats the same bytes as well, so what separates the two is time: a copy
arrives while the original is still being received.

The frames are fed in through a single pdu_set, which forwards them in order. Feeding them
from one source per channel - the topology the receiver actually has - makes the test racy
instead: the monitor stops as soon as the first source is done, dropping whatever is still
queued behind it. The channel a frame arrived on is metadata, so it can be set per frame.
"""

import pmt
from gnuradio import gr, gr_unittest, pdu

try:
    from gnuradio.wisun import pdu_duplicate_monitor
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import pdu_duplicate_monitor

CHANNEL_KEY = "packet-channel-number"


class qa_pdu_duplicate_monitor(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def monitor(self, frames_per_channel, window_ms=100):
        """Feed the frames of each channel in order and return the monitor for inspection."""
        monitor = pdu_duplicate_monitor(window_ms)
        # the source only has to forward; it adds a key of its own, which nothing reads
        source = pdu.pdu_set(pmt.string_to_symbol("test-source"), pmt.from_long(1))
        self.tb.msg_connect((source, 'pdus'), (monitor, 'pdus'))

        for channel, frames in frames_per_channel:
            metadata = pmt.dict_add(pmt.make_dict(), pmt.string_to_symbol(CHANNEL_KEY),
                                    pmt.from_long(channel))
            for frame in frames:
                source.to_basic_block()._post(
                    pmt.intern("pdus"),
                    pmt.cons(metadata, pmt.init_u8vector(len(frame), frame)))
        # only the source is told to finish: done reaches the monitor along the message edge
        # once the frames have, where telling it directly would end it before they arrive
        source.to_basic_block()._post(pmt.intern("system"),
                                      pmt.cons(pmt.intern("done"), pmt.from_long(1)))

        self.tb.start()
        self.tb.wait()
        return monitor

    def test_001_distinct_frames_are_not_duplicates(self):
        """Frames that differ must pass unremarked, however many there are."""
        monitor = self.monitor([(channel, [list(range(channel, channel + 20))])
                                for channel in range(10)])

        self.assertEqual(monitor.duplicates(), 0)

    def test_002_the_same_frame_on_another_channel_is_a_duplicate(self):
        """One frame received twice at once is what the monitor is for."""
        frame = list(range(40))
        monitor = self.monitor([(4, [frame]), (29, [frame])])

        self.assertEqual(monitor.duplicates(), 1)

    def test_003_a_duplicate_is_found_behind_other_frames(self):
        """Other channels' frames arrive in between, so the comparison is not just pairwise."""
        frame = list(range(40))
        monitor = self.monitor([(4, [frame]),
                                (7, [list(range(100, 140))]),
                                (11, [list(range(200, 240))]),
                                (29, [frame])])

        self.assertEqual(monitor.duplicates(), 1)

    def test_004_frames_outside_the_window_are_not_duplicates(self):
        """Beyond the window the same bytes mean a retransmission, which is legitimate.

        A window of zero stands in for "arrived much later" here, since the test cannot make
        the clock move.
        """
        frame = list(range(40))
        monitor = self.monitor([(4, [frame, frame])], window_ms=0)

        self.assertEqual(monitor.duplicates(), 0)

    def test_005_two_copies_of_one_frame_are_reported_once_each(self):
        """A frame arriving three times must be reported for each copy, not just the first."""
        frame = list(range(40))
        monitor = self.monitor([(4, [frame]), (29, [frame]), (30, [frame])])

        self.assertEqual(monitor.duplicates(), 2)


if __name__ == '__main__':
    gr_unittest.run(qa_pdu_duplicate_monitor)
