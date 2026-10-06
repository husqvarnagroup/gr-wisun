#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Unit tests for the pdu_add_pcapng_header block.

Note: as currently implemented, the tests will fail on a big-endian machine.
"""

import struct
import time

import pmt
from gnuradio import blocks, gr, gr_unittest, pdu

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
        # 32 bytes of EPB, 12 bytes of options (flags plus end of options)
        self.assertEqual(block_total_length, len(payload) + 32 + 12)
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
        self.assertEqual(captured_packet_length, len(payload))
        self.assertEqual(original_packet_length, len(payload))

        # check payload
        self.assertEqual(data[28:-16], payload)

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
        self.assertEqual(link_type, 195)  # IEEE 802.15.4 with FCS

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
        # 32 bytes EPB, 4 byte TAP header (no TLVs), 12 bytes of options
        self.assertEqual(block_total_length, len(payload) + 32 + 4 + 12)
        block_total_length_dup = struct.unpack("<L", data_str[-4:])[0]
        self.assertEqual(block_total_length_dup, len(payload) + 32 + 4 + 12)

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
        self.assertEqual(data[32:-16], payload)

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
        # 32 bytes EPB, 12 byte TAP header (with RSSI), 12 bytes of options
        self.assertEqual(block_total_length, len(payload) + 32 + 12 + 12)
        block_total_length_dup = struct.unpack("<L", data_str[-4:])[0]
        self.assertEqual(block_total_length_dup, len(payload) + 32 + 12 + 12)

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
        self.assertEqual(data[40:-16], payload)


    def test_004_the_leading_blocks_are_written_once(self):
        """The section header and interface description go out once, not once per packet.

        A pcapng stream carries them at the start; repeating the interface description
        before every packet redefines the interface over and over, which is what the block
        used to do.
        """
        blk = pdu_add_pcapng_header(True, True, True)
        msg_debug = blocks.message_debug()
        self.tb.msg_connect((blk, 'pdus'), (msg_debug, 'store'))

        port = pmt.intern("pdus")
        payload = list(range(4)) + list(range(16))  # bogus SFD & PHR, then payload
        for _ in range(3):
            blk.to_basic_block()._post(port, pmt.cons(pmt.PMT_NIL,
                                                      pmt.init_u8vector(len(payload), payload)))
        blk.to_basic_block()._post(pmt.intern("system"),
                                   pmt.cons(pmt.intern("done"), pmt.from_long(1)))
        self.tb.start()
        self.tb.wait()

        block_types = []
        for i in range(msg_debug.num_messages()):
            data = bytes(pmt.u8vector_elements(pmt.cdr(msg_debug.get_message(i))))
            block_types.append(struct.unpack("<L", data[0:4])[0])

        self.assertEqual(block_types.count(0x0a0d0d0a), 1)  # section header block
        self.assertEqual(block_types.count(0x00000001), 1)  # interface description block
        self.assertEqual(block_types.count(0x00000006), 3)  # enhanced packet blocks
        # and they come first, in that order
        self.assertEqual(block_types[:2], [0x0a0d0d0a, 0x00000001])


    def tap_tlvs(self, data):
        """Return the TAP TLVs of one enhanced packet block, as {type: value bytes}."""
        tap_length = struct.unpack("<H", data[30:32])[0]
        tlvs, offset = {}, 32
        while offset < 28 + tap_length:
            tlv_type, tlv_length = struct.unpack("<HH", data[offset:offset + 4])
            tlvs[tlv_type] = data[offset + 4:offset + 4 + tlv_length]
            offset += 4 + (tlv_length + 3) // 4 * 4
        return tlvs

    def packet_block(self, metadata, payload):
        """Push one PDU through the block with TAP enabled and return its bytes."""
        blk = pdu_add_pcapng_header(False, False, True)
        msg_debug = blocks.message_debug()
        self.tb.msg_connect((blk, 'pdus'), (msg_debug, 'store'))
        blk.to_basic_block()._post(pmt.intern("pdus"),
                                   pmt.cons(metadata, pmt.init_u8vector(len(payload), payload)))
        blk.to_basic_block()._post(pmt.intern("system"),
                                   pmt.cons(pmt.intern("done"), pmt.from_long(1)))
        self.tb.start()
        self.tb.wait()
        self.assertEqual(1, msg_debug.num_messages())
        return bytes(pmt.u8vector_elements(pmt.cdr(msg_debug.get_message(0))))

    def test_005_the_fcs_type_is_declared(self):
        """The frame carries its check sequence, so its width has to be declared.

        Without the FCS type TLV a reader cannot tell the trailing octets from payload, and
        so cannot check the frame for itself. 1 means a 2-octet CRC, 2 a 4-octet one.
        """
        for phr_fcs_type, expected in ((0, 2), (1, 1)):
            metadata = pmt.dict_add(pmt.make_dict(),
                                    pmt.string_to_symbol("wisun-packet-phr-fcs-type"),
                                    pmt.from_long(phr_fcs_type))
            data = self.packet_block(metadata, list(range(20)))
            self.assertEqual(self.tap_tlvs(data)[0], bytes([expected]))
            self.setUp()

    def test_006_a_failed_frame_check_is_reported_in_the_packet_flags(self):
        """A frame whose check sequence failed must not reach a reader looking clean.

        pcapng's packet flags carry the CRC error bit for exactly this; the frame's own
        check sequence is in the capture too, so the two agree.
        """
        for valid, crc_error in ((True, False), (False, True)):
            metadata = pmt.dict_add(pmt.make_dict(),
                                    pmt.string_to_symbol("wisun-packet-phr-fcs-type"),
                                    pmt.from_long(0))
            metadata = pmt.dict_add(metadata, pmt.string_to_symbol("wisun-fcs-valid"),
                                    pmt.from_bool(valid))
            data = self.packet_block(metadata, list(range(20)))

            # the options sit between the padded payload and the block total length
            option_code, option_length = struct.unpack("<HH", data[-16:-12])
            flags = struct.unpack("<L", data[-12:-8])[0]
            self.assertEqual(option_code, 2)        # epb_flags
            self.assertEqual(option_length, 4)
            self.assertEqual(struct.unpack("<HH", data[-8:-4]), (0, 0))  # end of options
            self.assertEqual(bool(flags & (1 << 24)), crc_error)
            self.assertEqual(flags & 0x3, 1)        # inbound
            self.assertEqual((flags >> 5) & 0xf, 4)  # 4-octet FCS
            self.setUp()


if __name__ == '__main__':
    gr_unittest.run(qa_pdu_add_pcapng_header)
