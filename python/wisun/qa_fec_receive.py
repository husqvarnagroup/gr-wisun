#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""End-to-end test of the FEC receive chain, from on-air bits to a decoded packet.

This drives the bit-level part of baseband_channel_receiver — sync word correlation,
packet gating, data whitening, and FEC decoding — with frames from the reference
encoder. It is the test that pins down how the pieces fit together, in particular
the span that data whitening covers.
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
from gnuradio.wisun.baseband_channel_receiver import HEADER_BITS_CODED
from gnuradio.wisun.parameters import SUN_FSK_SFD_CODED


class fec_bit_receiver(gr.top_block):
    """The bit-level part of the coded receive chain, fed from a vector of bits."""

    def __init__(self, bits):
        """Build the flow graph."""
        gr.top_block.__init__(self, "fec_bit_receiver")
        self.source = blocks.vector_source_b(bits)
        self.correlate = wisun.correlate_sync_word_bb(SUN_FSK_SFD_CODED, True)
        self.gate = wisun.packet_data_gate_bb('wisun-packet')
        self.whitening = wisun.data_whitening_bb('wisun-packet', HEADER_BITS_CODED)
        self.pack = blocks.unpacked_to_packed_bb(1, gr.GR_LSB_FIRST)
        self.to_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'wisun-packet')
        self.decode = wisun.pdu_fec_decode()
        self.sink = blocks.message_debug()

        self.connect(self.source, self.correlate, self.gate, self.whitening, self.pack, self.to_pdu)
        self.msg_connect((self.to_pdu, 'pdus'), (self.decode, 'pdus'))
        self.msg_connect((self.decode, 'pdus'), (self.sink, 'store'))

    def packets(self):
        """Return the payload of every decoded packet."""
        return [bytes(pmt.u8vector_elements(pmt.cdr(self.sink.get_message(i))))
                for i in range(self.sink.num_messages())]

    def metadata(self, index, key):
        """Return a metadata value of the packet with the given index."""
        msg = self.sink.get_message(index)
        entry = pmt.dict_ref(pmt.car(msg), pmt.string_to_symbol(key), pmt.PMT_NIL)
        return None if pmt.is_null(entry) else pmt.to_python(entry)


class qa_fec_receive(gr_unittest.TestCase):
    """GNU Radio test case class."""

    def run_chain(self, bits):
        """Run the receive chain over the given bits and return it for inspection."""
        # the correlator needs to see past the end of the last packet, and the gate needs
        # the packet's bits to have been written, so pad the stream at the end
        tb = fec_bit_receiver(bits + [0] * 200)
        tb.run()
        return tb

    def test_001_single_frame(self):
        """A single coded frame must come out of the chain as its PSDU."""
        psdu = fec.append_fcs(bytes(range(138)))
        tb = self.run_chain(fec.on_air_bits(psdu))

        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][2:4], b'\x08\x8e')
        self.assertEqual(packets[0][4:], psdu)
        # a clean frame must decode with no corrections at all
        self.assertEqual(tb.metadata(0, 'wisun-fec-metric'), 0)
        self.assertTrue(tb.metadata(0, 'wisun-fcs-valid'))

    def test_002_packet_length_matches_the_uncoded_path(self):
        """The decoded packet must be the SFD, the PHY header and the whole PSDU."""
        psdu = fec.append_fcs(bytes(range(138)))
        tb = self.run_chain(fec.on_air_bits(psdu))
        self.assertEqual(len(tb.packets()[0]), 4 + len(psdu))

    def test_003_several_frames_of_different_lengths(self):
        """A sequence of frames must all be received, whatever their length."""
        # the frame sizes of the recorded PhyModeID 0x13 ping exchange
        psdus = [fec.append_fcs(bytes((i * 7 + j) % 256 for j in range(length - 4)))
                 for i, length in enumerate((169, 50, 142, 56))]
        bits = []
        for psdu in psdus:
            bits += fec.on_air_bits(psdu) + [0] * 40  # a gap between frames
        tb = self.run_chain(bits)

        packets = tb.packets()
        self.assertEqual(len(packets), len(psdus))
        for i, psdu in enumerate(psdus):
            self.assertEqual(len(packets[i]), 4 + len(psdu))
            self.assertEqual(packets[i][4:], psdu)
            self.assertEqual(tb.metadata(i, 'wisun-fec-metric'), 0)
            self.assertTrue(tb.metadata(i, 'wisun-fcs-valid'))

    def test_004_frame_with_zero_padding(self):
        """A transmitter padding with zeros rather than ones must be received too."""
        psdu = fec.append_fcs(b'zero padding')
        tb = self.run_chain(fec.on_air_bits(psdu, pad_value=0))

        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][4:], psdu)
        self.assertEqual(tb.metadata(0, 'wisun-fec-metric'), 0)

    def test_005_corrected_single_bit_error(self):
        """A single corrupted bit on air must be corrected, and show up in the metric."""
        psdu = fec.append_fcs(bytes(range(60)))
        bits = fec.on_air_bits(psdu)
        # damage a bit in the middle of the coded block, well past the PHY header
        bits[200] ^= 1
        tb = self.run_chain(bits)

        packets = tb.packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][4:], psdu)
        self.assertEqual(tb.metadata(0, 'wisun-fec-metric'), 1)
        self.assertTrue(tb.metadata(0, 'wisun-fcs-valid'))

    def test_006_whitening_span_matters(self):
        """A frame whose encoded PHY header was whitened as well must not be received.

        The encoded PHY header is the one part of a coded frame that is not whitened. A
        chain that gets that span wrong recovers nothing, and this checks it recovers
        nothing quietly rather than producing a plausible-looking packet: here the header
        no longer decodes to a usable frame length, so the packet is rejected outright.
        """
        psdu = fec.append_fcs(bytes(range(60)))
        bits = fec.on_air_bits(psdu)
        header_offset = 8 * fec.PREAMBLE_OCTETS + 16
        for i, m in enumerate(fec.pn9_sequence(32)):
            bits[header_offset + i] ^= m
        tb = self.run_chain(bits)

        self.assertNotIn(psdu, [packet[4:] for packet in tb.packets()])

    def test_007_uncoded_sfd_is_not_received(self):
        """Coded and uncoded networks can share a channel; this chain must ignore uncoded."""
        psdu = fec.append_fcs(bytes(range(60)))
        bits = fec.on_air_bits(psdu)
        # replace the coded SFD with the uncoded one
        sfd_offset = 8 * fec.PREAMBLE_OCTETS
        bits[sfd_offset:sfd_offset + 16] = fec.bits_msb_first(fec.SFD_UNCODED, 16)
        tb = self.run_chain(bits)

        self.assertEqual(len(tb.packets()), 0)


if __name__ == '__main__':
    gr_unittest.run(qa_fec_receive)
