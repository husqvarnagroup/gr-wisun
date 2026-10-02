#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Tests for pdu_fcs_check block."""

import pmt
from gnuradio import blocks, gr, gr_unittest

try:
    from gnuradio.wisun import pdu_fcs_check
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import pdu_fcs_check
from gnuradio.wisun import fec

SFD_OCTETS = b'\x90\x4e'


def reverse_bits(octet):
    """Reverse the bits of an octet, as the stream domain packs the SFD and PHR."""
    return int(f"{octet:08b}"[::-1], 2)


def make_pdu(phr, psdu, sfd_octets=SFD_OCTETS, metadata=None):
    """Build a PDU as the uncoded stream part of the receive chain would deliver it.

    The SFD and PHY header arrive bit-reversed within each octet in the real chain
    (see `pdu_fcs_check_impl.cc`); this reproduces that here so the block is tested
    against its actual input convention rather than a convenient one.
    """
    phr_octets = bytes([reverse_bits(phr >> 8), reverse_bits(phr & 0xff)])
    data = bytes(sfd_octets) + phr_octets + bytes(psdu)
    meta = pmt.make_dict() if metadata is None else metadata
    return pmt.cons(meta, pmt.init_u8vector(len(data), list(data)))


class qa_pdu_fcs_check(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()
        self.blk = None
        self.dbg = None

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def check(self, pdus, drop_invalid_frames=False):
        """Run the given PDUs through the block and return the resulting messages."""
        self.blk = pdu_fcs_check(drop_invalid_frames)
        self.dbg = blocks.message_debug()
        self.tb.msg_connect((self.blk, 'pdus'), (self.dbg, 'store'))
        self.tb.start()
        for pdu in pdus:
            self.blk.to_basic_block()._post(pmt.intern('pdus'), pdu)
        self.blk.to_basic_block()._post(pmt.intern('system'),
                                        pmt.cons(pmt.intern('done'), pmt.from_long(1)))
        self.tb.wait()
        return [self.dbg.get_message(i) for i in range(self.dbg.num_messages())]

    @staticmethod
    def payload_of(msg):
        """Return the payload octets of a message."""
        return bytes(pmt.u8vector_elements(pmt.cdr(msg)))

    @staticmethod
    def metadata_of(msg, key):
        """Return a metadata value of a message, or None if it is absent."""
        entry = pmt.dict_ref(pmt.car(msg), pmt.string_to_symbol(key), pmt.PMT_NIL)
        if pmt.is_null(entry):
            return None
        return pmt.to_python(entry)

    def test_instance(self):
        """Test to ensure block can be instantiated."""
        pdu_fcs_check()
        pdu_fcs_check(True)

    def test_001_valid_frame_is_forwarded(self):
        """A frame with a correct FCS must be forwarded with the FCS stripped."""
        payload = bytes(range(20))
        psdu = fec.append_fcs(payload)
        phr = fec.phr_value(len(psdu), whitened=True, fcs16=False)
        msgs = self.check([make_pdu(phr, psdu)])

        self.assertEqual(len(msgs), 1)
        out = self.payload_of(msgs[0])
        self.assertEqual(out[0:2], SFD_OCTETS)
        self.assertEqual(out[2:4], phr.to_bytes(2, 'big'))
        self.assertEqual(out[4:], payload)
        self.assertTrue(self.metadata_of(msgs[0], 'wisun-fcs-valid'))

    def test_002_two_octet_fcs(self):
        """A 2-octet FCS must be read with the right width and stripped correctly."""
        payload = b'short frame check sequence'
        psdu = fec.append_fcs(payload, fcs16=True)
        phr = fec.phr_value(len(psdu), whitened=True, fcs16=True)
        msgs = self.check([make_pdu(phr, psdu)])

        self.assertEqual(len(msgs), 1)
        out = self.payload_of(msgs[0])
        self.assertEqual(out[4:], payload)
        self.assertTrue(self.metadata_of(msgs[0], 'wisun-fcs-valid'))

    def test_003_invalid_fcs_is_forwarded_or_dropped(self):
        """A frame whose FCS fails must be forwarded by default and dropped on request."""
        payload = bytearray(b'corrupted payload')
        psdu = bytearray(fec.append_fcs(bytes(payload)))
        psdu[-1] ^= 0xff
        phr = fec.phr_value(len(psdu), whitened=True, fcs16=False)

        msgs = self.check([make_pdu(phr, bytes(psdu))])
        self.assertEqual(len(msgs), 1)
        self.assertFalse(self.metadata_of(msgs[0], 'wisun-fcs-valid'))

        self.setUp()
        msgs = self.check([make_pdu(phr, bytes(psdu))], drop_invalid_frames=True)
        self.assertEqual(len(msgs), 0)

    def test_004_short_pdu_is_dropped(self):
        """A PDU shorter than the SFD and PHY header cannot be a frame."""
        short_pdu = pmt.cons(pmt.make_dict(), pmt.init_u8vector(3, [0, 0, 0]))
        msgs = self.check([short_pdu])
        self.assertEqual(len(msgs), 0)

    def test_005_metadata_is_preserved(self):
        """Metadata from upstream must survive alongside the new FCS tag."""
        payload = bytes(range(10))
        psdu = fec.append_fcs(payload)
        phr = fec.phr_value(len(psdu), whitened=True, fcs16=False)
        meta = pmt.dict_add(pmt.make_dict(),
                            pmt.string_to_symbol('packet-channel-number'),
                            pmt.from_long(3))
        msgs = self.check([make_pdu(phr, psdu, metadata=meta)])

        self.assertEqual(len(msgs), 1)
        self.assertEqual(self.metadata_of(msgs[0], 'packet-channel-number'), 3)
        self.assertTrue(self.metadata_of(msgs[0], 'wisun-fcs-valid'))


if __name__ == '__main__':
    gr_unittest.run(qa_pdu_fcs_check)
