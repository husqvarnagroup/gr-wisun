#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for the pdu_add_pcapng_header block.

Note: as currently implemented, the tests will fail on a big-endian machine.
"""

import time
import struct

from gnuradio import gr, gr_unittest
from gnuradio import blocks, pdu
import pmt
try:
    from gnuradio.wisun import pdu_add_pcapng_header
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import pdu_add_pcapng_header


def make_tag(key, value, offset, srcid=None):
    """Create a tag."""
    tag = gr.tag_t()
    tag.key = pmt.string_to_symbol(key)
    tag.value = pmt.to_pmt(value)
    tag.offset = offset
    if srcid is not None:
        tag.srcid = pmt.to_pmt(srcid)
    return tag


class qa_pdu_add_pcapng_header(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def test_001_add_enhanced_packet_block(self):
        """Test for adding of EPB header to payload."""
        header = [0x10, 0x11, 0x12, 0x13]  # bogus SFD & PHR (will be discarded)
        payload = [
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
        ]
        src_data = header + payload

        blk = pdu_add_pcapng_header(False, False, False)
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

        # check header: block type
        block_type = struct.unpack("<L", data_str[0:4])[0]
        self.assertEqual(block_type, 6)

        # check header: block_total_length
        block_total_length = struct.unpack("<L", data_str[4:8])[0]
        self.assertEqual(block_total_length, len(payload) + 32)  # EPB header itself takes 32 bytes
        block_total_length_dup = struct.unpack("<L", data_str[-4:])[0]
        self.assertEqual(block_total_length_dup, len(payload) + 32)  # EPB header itself takes 32 bytes

        # check header: interface ID
        interface_id = struct.unpack("<L", data_str[8:12])[0]
        self.assertEqual(interface_id, 0)

        # check header: timestamp
        timestamp_high = struct.unpack("<L", data_str[12:16])[0]
        timestamp_low = struct.unpack("<L", data_str[16:20])[0]
        timestamp = ((timestamp_high << 32) + timestamp_low) / 1e6
        now = time.time()
        self.assertAlmostEqual(timestamp, now, places=1)

        # check header: payload length
        captured_packet_length = struct.unpack("<L", data_str[20:24])[0]
        original_packet_length = struct.unpack("<L", data_str[24:28])[0]
        self.assertEqual(captured_packet_length, len(payload))
        self.assertEqual(original_packet_length, len(payload))

        # check payload
        self.assertEqual(data[28:-4], payload)

    def test_002_add_global_header_and_packet_record_header(self):
        """Test adding of PCAPNG SHB & IDB initially."""
        header = [0x10, 0x11, 0x12, 0x13]  # bogus SFD & PHR
        payload = [
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
        ]
        src_data = header + payload

        blk = pdu_add_pcapng_header(True, True, False)
        msg_debug = blocks.message_debug()
        self.tb.msg_connect((blk, 'pdus'), (msg_debug, 'store'))

        port = pmt.intern("pdus")
        msg = pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(src_data), src_data))
        blk.to_basic_block()._post(port, msg)
        blk.to_basic_block()._post(pmt.intern("system"),
                                   pmt.cons(pmt.intern("done"), pmt.from_long(1)))

        self.tb.start()
        self.tb.wait()

        self.assertEqual(3, msg_debug.num_messages())  # SHB, IDB & EPB
        shb_msg = msg_debug.get_message(0)
        idb_msg = msg_debug.get_message(1)

        #
        # check SHB
        #
        self.assertTrue(pmt.is_u8vector(pmt.cdr(shb_msg)))
        data = pmt.u8vector_elements(pmt.cdr(shb_msg))
        data_str = bytes(data)

        # block type
        self.assertEqual(data[0:4], [0x0a, 0x0d, 0x0d, 0x0a])

        # byte-order magic
        bom = struct.unpack("<L", data_str[8:12])[0]
        self.assertEqual(bom, 0x1a2b3c4d)

        # major & minor version
        major = struct.unpack("<H", data_str[12:14])[0]
        minor = struct.unpack("<H", data_str[14:16])[0]
        self.assertEqual(major, 1)
        self.assertEqual(minor, 0)

        #
        # check IDB
        #
        self.assertTrue(pmt.is_u8vector(pmt.cdr(idb_msg)))
        data = pmt.u8vector_elements(pmt.cdr(idb_msg))
        data_str = bytes(data)

        # block type
        block_type = struct.unpack("<L", data_str[0:4])[0]
        self.assertEqual(block_type, 1)

        # link type
        link_type = struct.unpack("<H", data_str[8:10])[0]
        self.assertEqual(link_type, 230)

    def test_003_tap_packet_with_shb_and_idb_and_epb(self):
        """Test TAP packet."""
        header = [0x10, 0x11, 0x12, 0x13]  # bogus SFD & PHR
        payload = [
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
        ]
        src_data = header + payload

        blk = pdu_add_pcapng_header(True, True, True)
        msg_debug = blocks.message_debug()
        self.tb.msg_connect((blk, 'pdus'), (msg_debug, 'store'))

        port = pmt.intern("pdus")
        msg = pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(src_data), src_data))
        blk.to_basic_block()._post(port, msg)
        blk.to_basic_block()._post(pmt.intern("system"),
                                   pmt.cons(pmt.intern("done"), pmt.from_long(1)))

        self.tb.start()
        self.tb.wait()

        self.assertEqual(3, msg_debug.num_messages())  # SHB, IDB & EPB
        shb_msg = msg_debug.get_message(0)
        idb_msg = msg_debug.get_message(1)
        epb_msg = msg_debug.get_message(2)

        #
        # check SHB
        #
        self.assertTrue(pmt.is_u8vector(pmt.cdr(shb_msg)))
        data = pmt.u8vector_elements(pmt.cdr(shb_msg))
        data_str = bytes(data)

        # block type
        self.assertEqual(data[0:4], [0x0a, 0x0d, 0x0d, 0x0a])

        # byte-order magic
        bom = struct.unpack("<L", data_str[8:12])[0]
        self.assertEqual(bom, 0x1a2b3c4d)

        # major & minor version
        major = struct.unpack("<H", data_str[12:14])[0]
        minor = struct.unpack("<H", data_str[14:16])[0]
        self.assertEqual(major, 1)
        self.assertEqual(minor, 0)

        #
        # check IDB
        #
        self.assertTrue(pmt.is_u8vector(pmt.cdr(idb_msg)))
        data = pmt.u8vector_elements(pmt.cdr(idb_msg))
        data_str = bytes(data)

        # block type
        block_type = struct.unpack("<L", data_str[0:4])[0]
        self.assertEqual(block_type, 1)

        # link type
        link_type = struct.unpack("<H", data_str[8:10])[0]
        self.assertEqual(link_type, 283)

        #
        # EPB
        #
        self.assertTrue(pmt.is_u8vector(pmt.cdr(epb_msg)))
        data = pmt.u8vector_elements(pmt.cdr(epb_msg))
        data_str = bytes(data)

        # check header: block type
        block_type = struct.unpack("<L", data_str[0:4])[0]
        self.assertEqual(block_type, 6)

        # check header: block_total_length
        block_total_length = struct.unpack("<L", data_str[4:8])[0]
        self.assertEqual(block_total_length, len(payload) + 32 + 4)  # 32 bytes EPB, 4 byte TAP header (no data)
        block_total_length_dup = struct.unpack("<L", data_str[-4:])[0]
        self.assertEqual(block_total_length_dup, len(payload) + 32 + 4)

        # check header: interface ID
        interface_id = struct.unpack("<L", data_str[8:12])[0]
        self.assertEqual(interface_id, 0)

        # check header: timestamp
        timestamp_high = struct.unpack("<L", data_str[12:16])[0]
        timestamp_low = struct.unpack("<L", data_str[16:20])[0]
        timestamp = ((timestamp_high << 32) + timestamp_low) / 1e6
        now = time.time()
        self.assertAlmostEqual(timestamp, now, places=1)

        # check header: payload length
        captured_packet_length = struct.unpack("<L", data_str[20:24])[0]
        original_packet_length = struct.unpack("<L", data_str[24:28])[0]
        self.assertEqual(captured_packet_length, len(payload) + 4)
        self.assertEqual(original_packet_length, len(payload) + 4)

        # payload: TAP header
        tap_version = data[28]
        tap_padding = data[29]
        tap_length = struct.unpack("<H", data_str[30:32])[0]
        self.assertEqual(tap_version, 0)
        self.assertEqual(tap_padding, 0)
        self.assertEqual(tap_length, 4)

        # payload: actual data
        self.assertEqual(data[32:-4], payload)

    def test_004_tap_packet_with_rssi(self):
        """Test TAP packet."""
        header = [0x10, 0x11, 0x12, 0x13]  # bogus SFD & PHR
        payload = [
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
        ]
        src_data = header + payload

        src = blocks.vector_source_b(src_data,
                                     tags=(
                                         make_tag('wisun-packet', 20, 0),
                                         make_tag('packet-rssi', -40.5, 0),
                                     ))
        tagged_stream_to_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'wisun-packet')
        blk = pdu_add_pcapng_header(False, False, True)
        msg_debug = blocks.message_debug()

        self.tb.connect((src, 0), (tagged_stream_to_pdu, 0))
        self.tb.msg_connect((tagged_stream_to_pdu, 'pdus'), (blk, 'pdus'))
        self.tb.msg_connect((blk, 'pdus'), (msg_debug, 'store'))

        self.tb.start()
        self.tb.wait()

        self.assertEqual(1, msg_debug.num_messages())  # only expecting EPB
        epb_msg = msg_debug.get_message(0)

        #
        # EPB
        #
        self.assertTrue(pmt.is_u8vector(pmt.cdr(epb_msg)))
        data = pmt.u8vector_elements(pmt.cdr(epb_msg))
        data_str = bytes(data)

        # check header: block type
        block_type = struct.unpack("<L", data_str[0:4])[0]
        self.assertEqual(block_type, 6)

        # check header: block_total_length
        block_total_length = struct.unpack("<L", data_str[4:8])[0]
        self.assertEqual(block_total_length, len(payload) + 32 + 12)  # 32 bytes EPB, 12 byte TAP header (with RSSI)
        block_total_length_dup = struct.unpack("<L", data_str[-4:])[0]
        self.assertEqual(block_total_length_dup, len(payload) + 32 + 12)

        # check header: interface ID
        interface_id = struct.unpack("<L", data_str[8:12])[0]
        self.assertEqual(interface_id, 0)

        # check header: timestamp
        timestamp_high = struct.unpack("<L", data_str[12:16])[0]
        timestamp_low = struct.unpack("<L", data_str[16:20])[0]
        timestamp = ((timestamp_high << 32) + timestamp_low) / 1e6
        now = time.time()
        self.assertAlmostEqual(timestamp, now, places=1)

        # check header: payload length
        captured_packet_length = struct.unpack("<L", data_str[20:24])[0]
        original_packet_length = struct.unpack("<L", data_str[24:28])[0]
        self.assertEqual(captured_packet_length, len(payload) + 12)
        self.assertEqual(original_packet_length, len(payload) + 12)

        # payload: TAP header
        tap_version = data[28]
        tap_padding = data[29]
        tap_length = struct.unpack("<H", data_str[30:32])[0]
        self.assertEqual(tap_version, 0)
        self.assertEqual(tap_padding, 0)
        self.assertEqual(tap_length, 12)

        # payload: TAP RSSI
        tlv_type = struct.unpack("<H", data_str[32:34])[0]
        tlv_length = struct.unpack("<H", data_str[34:36])[0]
        tlv_value = struct.unpack("<f", data_str[36:40])[0]
        self.assertEqual(tlv_type, 1)  # type: RSS
        self.assertEqual(tlv_length, 4)  # length: 4
        self.assertEqual(tlv_value, -40.5)

        # payload: actual data
        self.assertEqual(data[40:-4], payload)


if __name__ == '__main__':
    gr_unittest.run(qa_pdu_add_pcapng_header)
