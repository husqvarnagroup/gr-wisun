#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Tests for pdu_fec_decode block."""

import random

from gnuradio import blocks, gr, gr_unittest
import pmt
try:
    from gnuradio.wisun import pdu_fec_decode
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio.wisun import pdu_fec_decode
from gnuradio.wisun import fec

SFD_OCTETS = b'\x6f\x4e'


def make_pdu(coded_octets, sfd_octets=SFD_OCTETS, metadata=None):
    """Build a PDU as the stream part of the receive chain would deliver it."""
    data = bytes(sfd_octets) + bytes(coded_octets)
    meta = pmt.make_dict() if metadata is None else metadata
    return pmt.cons(meta, pmt.init_u8vector(len(data), list(data)))


def coded_octets_for(psdu, pad_value=1, fcs16=False):
    """Encode a PSDU the way a transmitter would and de-whiten it again.

    This block sees the code symbols after data_whitening_bb has run over them in
    the stream domain, so the whitening of the PSDU's code symbols is already
    undone here. The PHY header still says the frame was whitened, because it was.
    """
    code_bits = fec.encode_frame(psdu, whitened=True, fcs16=fcs16, pad_value=pad_value)
    mask = fec.pn9_sequence(len(code_bits) - 32)
    code_bits = code_bits[:32] + [bit ^ m for bit, m in zip(code_bits[32:], mask)]
    return fec.bits_to_octets(code_bits)


class qa_pdu_fec_decode(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def setUp(self):
        """Set up top block."""
        self.tb = gr.top_block()
        self.blk = None
        self.dbg = None

    def tearDown(self):
        """Teardown."""
        self.tb = None

    def decode(self, pdus, drop_invalid_frames=False):
        """Run the given PDUs through the block and return the resulting messages."""
        self.blk = pdu_fec_decode(drop_invalid_frames)
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
        """Return the payload octets of a decoded message."""
        return bytes(pmt.u8vector_elements(pmt.cdr(msg)))

    @staticmethod
    def metadata_of(msg, key):
        """Return a metadata value of a decoded message, or None if it is absent."""
        entry = pmt.dict_ref(pmt.car(msg), pmt.string_to_symbol(key), pmt.PMT_NIL)
        if pmt.is_null(entry):
            return None
        return pmt.to_python(entry)

    def test_instance(self):
        """Test to ensure block can be instantiated."""
        pdu_fec_decode()
        pdu_fec_decode(True)

    def test_001_decodes_a_frame(self):
        """A coded frame must come back as its PHY header and PSDU."""
        psdu = fec.append_fcs(bytes(range(138)))
        msgs = self.decode([make_pdu(coded_octets_for(psdu))])

        self.assertEqual(len(msgs), 1)
        payload = self.payload_of(msgs[0])
        # SFD, PHY header most significant octet first, then the PSDU without its FCS
        self.assertEqual(payload[0:2], SFD_OCTETS)
        self.assertEqual(payload[2:4], b'\x08\x8e')
        self.assertEqual(payload[4:], psdu[:-4])
        # a clean frame needs no corrections at all
        self.assertEqual(self.metadata_of(msgs[0], 'wisun-fec-metric'), 0)
        self.assertTrue(self.metadata_of(msgs[0], 'wisun-fcs-valid'))

    def test_002_pdu_length_matches_the_uncoded_path(self):
        """The decoded PDU must be as long as the uncoded path's, i.e. the frame length."""
        for payload_length in (4, 44, 138, 165):
            psdu = fec.append_fcs(bytes(range(payload_length % 256))[:payload_length])
            msgs = self.decode([make_pdu(coded_octets_for(psdu))])
            self.assertEqual(len(self.payload_of(msgs[0])), len(psdu))
            self.setUp()

    def test_003_padding_value_does_not_matter(self):
        """Real transmitters pad with ones; the decoder must not depend on either value."""
        psdu = fec.append_fcs(b'padding value must not matter')
        for pad_value in (0, 1):
            msgs = self.decode([make_pdu(coded_octets_for(psdu, pad_value=pad_value))])
            self.assertEqual(len(msgs), 1)
            self.assertEqual(self.payload_of(msgs[0])[4:], psdu[:-4])
            self.assertEqual(self.metadata_of(msgs[0], 'wisun-fec-metric'), 0)
            self.setUp()

    def test_004_two_octet_fcs(self):
        """With a 2-octet FCS, 2 octets must be stripped rather than 4."""
        psdu = fec.append_fcs(b'short frame check sequence', fcs16=True)
        msgs = self.decode([make_pdu(coded_octets_for(psdu, fcs16=True))])

        payload = self.payload_of(msgs[0])
        # whitened, FCS-16, and the frame length of this PSDU
        expected_phr = 0x1800 | len(psdu)
        self.assertEqual(payload[2:4], expected_phr.to_bytes(2, 'big'))
        self.assertEqual(payload[4:], psdu[:-2])
        self.assertTrue(self.metadata_of(msgs[0], 'wisun-fcs-valid'))

    def test_005_single_bit_error_sweep(self):
        """Every single-bit error must be corrected, at a path metric of exactly 1.

        This is what catches a traceback that walks one stage too far, which
        otherwise only shows up as rare, length-dependent failures.
        """
        psdu = fec.append_fcs(b'sweep')
        coded = coded_octets_for(psdu)
        pdus = []
        for octet in range(len(coded)):
            for bit in range(8):
                damaged = bytearray(coded)
                damaged[octet] ^= 1 << bit
                pdus.append(make_pdu(bytes(damaged)))
        msgs = self.decode(pdus)

        self.assertEqual(len(msgs), 8 * len(coded))
        for i, msg in enumerate(msgs):
            self.assertEqual(self.payload_of(msg)[4:], psdu[:-4],
                             f"bit {i} was not corrected")
            self.assertEqual(self.metadata_of(msg, 'wisun-fec-metric'), 1,
                             f"unexpected path metric for a single error in bit {i}")
            self.assertTrue(self.metadata_of(msg, 'wisun-fcs-valid'))

    def test_006_random_data_is_rejected(self):
        """Random data must be rejected by the path metric, not accepted as a frame."""
        random.seed(20260929)
        pdus = [make_pdu(bytes(random.getrandbits(8) for _ in range(108)))
                for _ in range(20)]
        msgs = self.decode(pdus)

        # a random bit pair disagrees with the best branch about a quarter of the
        # time, which is far above the guard, so nothing may come through
        self.assertEqual(len(msgs), 0)

    def test_007_invalid_fcs_is_forwarded_or_dropped(self):
        """A frame whose FCS fails must be forwarded by default and dropped on request."""
        psdu = bytearray(fec.append_fcs(b'corrupted payload'))
        psdu[-1] ^= 0xff  # break the frame check sequence, not the coding
        coded = coded_octets_for(bytes(psdu))

        msgs = self.decode([make_pdu(coded)])
        self.assertEqual(len(msgs), 1)
        self.assertFalse(self.metadata_of(msgs[0], 'wisun-fcs-valid'))
        self.assertEqual(self.metadata_of(msgs[0], 'wisun-fec-metric'), 0)

        self.setUp()
        msgs = self.decode([make_pdu(coded)], drop_invalid_frames=True)
        self.assertEqual(len(msgs), 0)

    def test_008_incomplete_interleaver_block_is_dropped(self):
        """A PDU that is not a whole number of interleaver blocks cannot be a frame."""
        psdu = fec.append_fcs(b'truncated')
        coded = coded_octets_for(psdu)
        msgs = self.decode([make_pdu(coded[:-1]), make_pdu(b''), make_pdu(b'\x00')])
        self.assertEqual(len(msgs), 0)

    def test_009_metadata_is_preserved(self):
        """Metadata from upstream must survive, and a header mismatch must not be fatal."""
        psdu = fec.append_fcs(bytes(range(60)))
        meta = pmt.dict_add(pmt.make_dict(),
                            pmt.string_to_symbol('packet-channel-number'),
                            pmt.from_long(7))
        meta = pmt.dict_add(meta, pmt.string_to_symbol('wisun-packet-phr'),
                            pmt.from_long(0x0840))
        msgs = self.decode([make_pdu(coded_octets_for(psdu), metadata=meta)])

        self.assertEqual(len(msgs), 1)
        self.assertEqual(self.metadata_of(msgs[0], 'packet-channel-number'), 7)
        self.assertEqual(self.metadata_of(msgs[0], 'wisun-fec-metric'), 0)


if __name__ == '__main__':
    gr_unittest.run(qa_pdu_fec_decode)
