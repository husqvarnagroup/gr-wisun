#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for the pdu_add_pcap_header block."""

import time
import struct

from gnuradio import gr, gr_unittest
from gnuradio import blocks
import pmt
try:
    from gnuradio.wisun import pdu_add_pcap_header
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import pdu_add_pcap_header


class qa_pdu_add_pcap_header(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def test_001_add_packet_record_header(self):
        """Test adding of PCAP packet record header to a short packet."""
        header = [0x10, 0x11, 0x12, 0x13]  # bogus SFD & PHR
        payload = [
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
        ]
        src_data = header + payload

        blk = pdu_add_pcap_header(False)
        msg_debug = blocks.message_debug()
        self.tb.msg_connect((blk, 'pdus'), (msg_debug, 'store'))

        port = pmt.intern("pdus")
        msg = pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(src_data), src_data))
        blk.to_basic_block()._post(port, msg)
        blk.to_basic_block()._post(pmt.intern("system"),
                                   pmt.cons(pmt.intern("done"), pmt.from_long(1)))

        self.tb.start()
        self.tb.wait()

        self.assertEqual(1, msg_debug.num_messages())
        msg = msg_debug.get_message(0)
        self.assertTrue(pmt.is_u8vector(pmt.cdr(msg)))
        data = pmt.u8vector_elements(pmt.cdr(msg))
        data_str = bytes(data)

        # check header: timestamp (seconds)
        timestamp = struct.unpack("<L", data_str[0:4])[0]
        now = int(time.time())
        self.assertTrue(timestamp == now or timestamp + 1 == now)

        # check header: length
        actual_length = struct.unpack("<L", data_str[8:12])[0]
        self.assertEqual(actual_length, len(payload))
        original_length = struct.unpack("<L", data_str[12:16])[0]
        self.assertEqual(original_length, len(payload))

        # check data
        self.assertEqual(len(payload) + 16, len(data))
        self.assertEqual(data[16:], payload)

    def test_002_add_global_header_and_packet_record_header(self):
        """Test adding of PCAP packet record header to a short packet."""
        header = [0x10, 0x11, 0x12, 0x13]  # bogus SFD & PHR
        payload = [
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
        ]
        src_data = header + payload

        blk = pdu_add_pcap_header(True)
        msg_debug = blocks.message_debug()
        self.tb.msg_connect((blk, 'pdus'), (msg_debug, 'store'))

        port = pmt.intern("pdus")
        msg = pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(src_data), src_data))
        blk.to_basic_block()._post(port, msg)
        blk.to_basic_block()._post(pmt.intern("system"),
                                   pmt.cons(pmt.intern("done"), pmt.from_long(1)))

        self.tb.start()
        self.tb.wait()

        self.assertEqual(2, msg_debug.num_messages())  # one packet with global PCAP header, one PCAP record
        msg = msg_debug.get_message(0)
        self.assertTrue(pmt.is_u8vector(pmt.cdr(msg)))
        data = pmt.u8vector_elements(pmt.cdr(msg))
        data_str = bytes(data)

        # check header: magic number
        magic_number = struct.unpack("<L", data_str[0:4])[0]
        self.assertEqual(magic_number, 0xa1b2c3d4)

        # check header: major & minor version
        major_version = struct.unpack("<H", data_str[4:6])[0]
        minor_version = struct.unpack("<H", data_str[6:8])[0]
        self.assertEqual(major_version, 2)
        self.assertEqual(minor_version, 0)

        # check header: reserved blocks
        reserved1 = struct.unpack("<L", data_str[8:12])[0]
        reserved2 = struct.unpack("<L", data_str[12:16])[0]
        self.assertEqual(reserved1, 0)
        self.assertEqual(reserved2, 0)

        # check header: snap len
        snap_len = struct.unpack("<L", data_str[16:20])[0]
        self.assertEqual(snap_len, 2047)

        # check header: link type
        link_type = struct.unpack("<L", data_str[20:24])[0]
        self.assertEqual(link_type, 230)


if __name__ == '__main__':
    gr_unittest.run(qa_pdu_add_pcap_header)
