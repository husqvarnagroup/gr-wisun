#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""End-to-end test of the uncoded receive chain, from on-air bits to a checked packet.

This drives the bit-level part of baseband_channel_receiver -- sync word correlation,
packet gating, data whitening, and frame check sequence validation -- with a hand-built
uncoded frame. It is the test that pins down the uncoded framing arithmetic (the span to
gate from the SFD has to include the SFD and PHY header octets, not just the PSDU the
frame length field names) the same way qa_fec_receive.py pins down the coded chain.
"""

import pmt
from gnuradio import blocks, gr, gr_unittest, pdu

try:
    from gnuradio import wisun
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio import wisun
from gnuradio.wisun import fec
from gnuradio.wisun.baseband_channel_receiver import HEADER_BITS_UNCODED
from gnuradio.wisun.parameters import SUN_FSK_SFD_UNCODED

PREAMBLE_OCTETS = 8


def on_air_bits(psdu, whitened=True, fcs16=False):
    """Build a complete uncoded frame as it appears on air, SHR included.

    Unlike a coded frame, the PSDU is transmitted as-is, with no convolutional
    coding or interleaving -- only whitening applies, covering the PSDU alone.
    """
    preamble = fec.octets_to_bits([fec.PREAMBLE_OCTET] * PREAMBLE_OCTETS)
    sfd = fec.bits_msb_first(SUN_FSK_SFD_UNCODED, 16)
    phr = fec.phr_value(len(psdu), whitened=whitened, fcs16=fcs16)
    phr_bits = fec.bits_msb_first(phr, 16)
    psdu_bits = fec.octets_to_bits(psdu)
    if whitened:
        mask = fec.pn9_sequence(len(psdu_bits))
        psdu_bits = [bit ^ m for bit, m in zip(psdu_bits, mask, strict=True)]
    return preamble + sfd + phr_bits + psdu_bits


class uncoded_bit_receiver(gr.top_block):
    """The bit-level part of the uncoded receive chain, fed from a vector of bits."""

    def __init__(self, bits):
        """Build the flow graph."""
        gr.top_block.__init__(self, "uncoded_bit_receiver")
        self.source = blocks.vector_source_b(bits)
        self.correlate = wisun.correlate_sync_word_bb(SUN_FSK_SFD_UNCODED, False)
        self.gate = wisun.packet_data_gate_bb('wisun-packet')
        self.whitening = wisun.data_whitening_bb('wisun-packet', HEADER_BITS_UNCODED)
        self.pack = blocks.unpacked_to_packed_bb(1, gr.GR_LSB_FIRST)
        self.to_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'wisun-packet')
        self.fcs_check = wisun.pdu_fcs_check()
        self.sink = blocks.message_debug()

        self.connect(self.source, self.correlate, self.gate, self.whitening, self.pack, self.to_pdu)
        self.msg_connect((self.to_pdu, 'pdus'), (self.fcs_check, 'pdus'))
        self.msg_connect((self.fcs_check, 'pdus'), (self.sink, 'store'))

    def packets(self):
        """Return the payload of every checked packet."""
        return [bytes(pmt.u8vector_elements(pmt.cdr(self.sink.get_message(i))))
                for i in range(self.sink.num_messages())]

    def metadata(self, index, key):
        """Return a metadata value of the packet with the given index."""
        msg = self.sink.get_message(index)
        entry = pmt.dict_ref(pmt.car(msg), pmt.string_to_symbol(key), pmt.PMT_NIL)
        return None if pmt.is_null(entry) else pmt.to_python(entry)


class qa_uncoded_receive(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def run_chain(self, bits):
        """Run the receive chain over the given bits and return it for inspection."""
        # the correlator needs to see past the end of the last packet, and the gate needs
        # the packet's bits to have been written, so pad the stream at the end
        tb = uncoded_bit_receiver(bits + [0] * 200)
        tb.run()
        return tb

    def test_001_single_frame(self):
        """A single uncoded frame must come out of the chain as its payload."""
        payload = bytes(range(138))
        psdu = fec.append_fcs(payload)
        tb = self.run_chain(on_air_bits(psdu))

        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][4:], psdu)
        self.assertTrue(tb.metadata(0, 'wisun-fcs-valid'))

    def test_002_two_octet_fcs(self):
        """A 2-octet FCS frame must be framed correctly: this is what the framing fix covers.

        Before the fix, the span gated from the SFD was the PHR frame length alone,
        4 octets short of the whole frame; for a 2-octet FCS that silently dropped the
        last 2 octets of payload along with the FCS, rather than just the FCS.
        """
        payload = bytes(range(60))
        psdu = fec.append_fcs(payload, fcs16=True)
        tb = self.run_chain(on_air_bits(psdu, fcs16=True))

        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][4:], psdu)
        self.assertTrue(tb.metadata(0, 'wisun-fcs-valid'))

    def test_003_several_frames_of_different_lengths(self):
        """A sequence of frames must all be received, whatever their length."""
        payloads = [bytes((i * 7 + j) % 256 for j in range(length))
                    for i, length in enumerate((20, 46, 138, 52))]
        bits = []
        for payload in payloads:
            bits += on_air_bits(fec.append_fcs(payload)) + [0] * 40  # a gap between frames
        tb = self.run_chain(bits)

        packets = tb.packets()
        self.assertEqual(len(packets), len(payloads))
        for i, payload in enumerate(payloads):
            self.assertEqual(packets[i][4:], fec.append_fcs(payload))
            self.assertTrue(tb.metadata(i, 'wisun-fcs-valid'))

    def test_004_the_phy_header_agrees_with_the_correlator(self):
        """The header this chain packs and the one the correlator read must agree.

        The two are derived independently - pdu_fcs_check from the packed octets, where the
        header is bit-reversed within each octet, the correlator from the bit stream - so
        this pins down that bit order, the easiest thing here to get wrong.
        """
        tb = self.run_chain(on_air_bits(fec.append_fcs(bytes(range(60)), fcs16=True),
                                        fcs16=True))
        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(int.from_bytes(packets[0][2:4], 'big'),
                         tb.metadata(0, 'wisun-packet-phr'))

    def test_005_corrupted_fcs_is_flagged(self):
        """A frame with a damaged frame check sequence must still come through, flagged."""
        payload = b'corrupted payload'
        psdu = bytearray(fec.append_fcs(payload))
        psdu[-1] ^= 0xff
        tb = self.run_chain(on_air_bits(bytes(psdu)))

        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertFalse(tb.metadata(0, 'wisun-fcs-valid'))


if __name__ == '__main__':
    gr_unittest.run(qa_uncoded_receive)
