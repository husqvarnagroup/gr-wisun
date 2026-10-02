#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Hierarchical block to receive a single channel on baseband."""

import pmt
from gnuradio import analog, blocks, digital, gr, pdu, wisun
from gnuradio.wisun.parameters import SUN_FSK_SFD_CODED, SUN_FSK_SFD_UNCODED

RSSI_TAG_SYMBOLS = 20  # number of symbols to evaluate per RSSI-tag; should be < preamble length
DC_CORRECTION_SYMBOLS = 30  # number of symbols for DC correction estimation; should be < preamble length

# Number of leading bits of a packet that data whitening does not cover: the SFD, plus the
# PHY header. For a coded packet the PHY header is the first interleaver block, twice as
# long on air, and it is the one part of the frame that is not whitened.
HEADER_BITS_UNCODED = 16 + 16
HEADER_BITS_CODED = 16 + 32


class baseband_channel_receiver(gr.hier_block2):
    """Block to receive Wi-SUN packets on a single baseband channel (i.e. already filtered and centered to 0 Hz)."""

    def __init__(self, samples_per_symbol, sfd=None, fec=False, gated_power_squelch=False, metadata=None):
        """Initialize block.

        If `fec` is set, packets are expected to be FEC-coded (Wi-SUN PHY type 1). A coded mode changes
        nothing below the bits, so the receive chain up to and including the bit slicer is the same; what
        differs is the SFD to correlate against, the span data whitening covers, and the decoding of the
        packet data. Note that a receiver locked to one SFD is deaf to the other.
        """
        gr.hier_block2.__init__(self,
                                "baseband_channel_receiver",
                                gr.io_signature(1, 1, gr.sizeof_gr_complex),  # Input signature
                                gr.io_signature(0, 0, 0))  # Output signature

        self._samples_per_symbol = samples_per_symbol
        self._fec = fec
        if sfd is None:
            sfd = SUN_FSK_SFD_CODED if fec else SUN_FSK_SFD_UNCODED
        self._sfd = sfd
        self._metadata = {} if metadata is None else metadata

        ##################################################
        # Blocks
        ##################################################
        if gated_power_squelch:
            self.power_squelch_block = wisun.gated_power_squelch_relative_cc(20, 0.01, 1000)
        else:
            self.power_squelch_block = wisun.power_squelch_relative_cc(20, 0.01)
        self.rssi_tag_block = wisun.rssi_tag_cc(self._samples_per_symbol * RSSI_TAG_SYMBOLS)
        self.fm_demod_block = analog.quadrature_demod_cf(1)
        self.dc_correction_block = wisun.tag_based_dc_correction_ff('squelch_sob', 'squelch_eob',
                                                                    self._samples_per_symbol * DC_CORRECTION_SYMBOLS)
        self.agc_block = analog.agc_ff(1e-4, 1.0, 1.0, 1.5)
        # loop bandwidth and damping, measured against gr-wisun-test-suite's SNR,
        # carrier-offset and clock-error sweeps rather than taken from a textbook: 0.18/1.0
        # beat the previous 0.045/1 in aggregate on all three, on a plateau spanning
        # loop_bw 0.15 to 0.25, and recovers a clock-error point that collapsed entirely
        self.symbol_sync_block = digital.symbol_sync_ff(
            digital.TED_ZERO_CROSSING,
            self._samples_per_symbol,
            0.18,
            1.0,
            1.0,
            0.05,  # maximum deviation
            1,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.binary_slicer_block = digital.binary_slicer_fb()
        self.correlate_sync_word_block = wisun.correlate_sync_word_bb(self._sfd, self._fec)
        self.packet_data_gate_block = wisun.packet_data_gate_bb('wisun-packet')
        self.data_whitening_block = wisun.data_whitening_bb(
            'wisun-packet', HEADER_BITS_CODED if self._fec else HEADER_BITS_UNCODED)
        self.unpacked_to_packed_block = blocks.unpacked_to_packed_bb(1, gr.GR_LSB_FIRST)
        self.tagged_stream_to_pdu_block = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'wisun-packet')
        # both branches validate the frame check sequence before metadata tagging;
        # the coded one as a side effect of decoding, the uncoded one as its only job
        self.fcs_block = wisun.pdu_fec_decode() if self._fec else wisun.pdu_fcs_check()
        self.metadata_blocks = []

        for key in self._metadata:
            value = self._metadata[key]
            pmt_key = pmt.string_to_symbol(key)
            pmt_value = pmt.from_long(value)
            block = pdu.pdu_set(pmt_key, pmt_value)
            self.metadata_blocks.append(block)

        # if available, provide channel information to blocks
        # (this is only relevant for logging)
        if metadata is not None and 'packet-channel-number' in metadata:
            channel = metadata['packet-channel-number']
            self.correlate_sync_word_block.set_channel(channel)
            self.packet_data_gate_block.set_channel(channel)
            self.power_squelch_block.set_channel(channel)

        ##################################################
        # Connections
        ##################################################
        self.connect((self, 0), (self.power_squelch_block, 0))
        self.connect((self.power_squelch_block, 0), (self.rssi_tag_block, 0))
        self.connect((self.rssi_tag_block, 0), (self.fm_demod_block, 0))
        self.connect((self.fm_demod_block, 0), (self.dc_correction_block, 0))
        self.connect((self.dc_correction_block, 0), (self.agc_block, 0))
        self.connect((self.agc_block, 0), (self.symbol_sync_block, 0))
        self.connect((self.symbol_sync_block, 0), (self.binary_slicer_block, 0))
        self.connect((self.binary_slicer_block, 0), (self.correlate_sync_word_block, 0))
        self.connect((self.correlate_sync_word_block, 0), (self.packet_data_gate_block, 0))
        self.connect((self.packet_data_gate_block, 0), (self.data_whitening_block, 0))
        self.connect((self.data_whitening_block, 0), (self.unpacked_to_packed_block, 0))
        self.connect((self.unpacked_to_packed_block, 0), (self.tagged_stream_to_pdu_block, 0))
        self.message_port_register_hier_out('pdus')
        # FEC decoding and FCS checking happen per packet in the message domain, which
        # keeps them off the path that acquires the next packet
        message_blocks = [self.fcs_block, *self.metadata_blocks]
        previous_block = self.tagged_stream_to_pdu_block
        for block in message_blocks:
            self.msg_connect((previous_block, 'pdus'), (block, 'pdus'))
            previous_block = block
        self.msg_connect((previous_block, 'pdus'), (self, 'pdus'))
