#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Hierarchical block to receive a single channel on baseband."""

from gnuradio import analog, blocks, digital, gr, wisun, pdu
import pmt

RSSI_TAG_SYMBOLS = 20  # number of symbols to evaluate per RSSI-tag; should be < preamble length
DC_CORRECTION_SYMBOLS = 30  # number of symbols for DC correction estimation; should be < preamble length


class baseband_channel_receiver(gr.hier_block2):
    """Block to receive Wi-SUN packets on a single baseband channel (i.e. already filtered and centered to 0 Hz)."""

    def __init__(self, samples_per_symbol, sfd=0b1001000001001110, metadata=None, gated_power_squelch=False):
        """Initialize block."""
        gr.hier_block2.__init__(self,
                                "baseband_channel_receiver",
                                gr.io_signature(1, 1, gr.sizeof_gr_complex),  # Input signature
                                gr.io_signature(0, 0, 0))  # Output signature

        self._samples_per_symbol = samples_per_symbol
        self._sfd = sfd
        self._metadata = {} if metadata is None else metadata

        ##################################################
        # Blocks
        ##################################################
        self.rssi_tag_block = wisun.rssi_tag_cc(self._samples_per_symbol * RSSI_TAG_SYMBOLS)
        if gated_power_squelch:
            self.power_squelch_block = wisun.gated_power_squelch_relative_cc(20, 0.01, 1000)
        else:
            self.power_squelch_block = wisun.power_squelch_relative_cc(20, 0.01)
        self.fm_demod_block = analog.quadrature_demod_cf(1)
        self.dc_correction_block = wisun.tag_based_dc_correction_ff('squelch_sob', 'squelch_eob',
                                                                    self._samples_per_symbol * DC_CORRECTION_SYMBOLS)
        self.symbol_sync_block = digital.symbol_sync_ff(
            digital.TED_ZERO_CROSSING,
            self._samples_per_symbol,
            0.045,
            1,
            1.0,
            1.5,
            1,
            digital.constellation_bpsk().base(),
            digital.IR_MMSE_8TAP,
            128,
            [])
        self.binary_slicer_block = digital.binary_slicer_fb()
        self.correlate_sync_word_block = wisun.correlate_sync_word_bb(self._sfd)
        self.packet_data_gate_block = wisun.packet_data_gate_bb('wisun-packet')
        self.data_whitening_block = wisun.data_whitening_bb('wisun-packet', 32)
        self.unpacked_to_packed_block = blocks.unpacked_to_packed_bb(1, gr.GR_LSB_FIRST)
        self.tagged_stream_to_pdu_block = pdu.tagged_stream_to_pdu(gr.types.byte_t, 'wisun-packet')
        self.metadata_blocks = []

        for key in self._metadata:
            value = self._metadata[key]
            pmt_key = pmt.string_to_symbol(key)
            pmt_value = pmt.from_long(value)
            block = pdu.pdu_set(pmt_key, pmt_value)
            self.metadata_blocks.append(block)

        ##################################################
        # Connections
        ##################################################
        self.connect((self, 0), (self.rssi_tag_block, 0))
        self.connect((self.rssi_tag_block, 0), (self.power_squelch_block, 0))
        self.connect((self.power_squelch_block, 0), (self.fm_demod_block, 0))
        self.connect((self.fm_demod_block, 0), (self.dc_correction_block, 0))
        self.connect((self.dc_correction_block, 0), (self.symbol_sync_block, 0))
        self.connect((self.symbol_sync_block, 0), (self.binary_slicer_block, 0))
        self.connect((self.binary_slicer_block, 0), (self.correlate_sync_word_block, 0))
        self.connect((self.correlate_sync_word_block, 0), (self.packet_data_gate_block, 0))
        self.connect((self.packet_data_gate_block, 0), (self.data_whitening_block, 0))
        self.connect((self.data_whitening_block, 0), (self.unpacked_to_packed_block, 0))
        self.connect((self.unpacked_to_packed_block, 0), (self.tagged_stream_to_pdu_block, 0))
        self.message_port_register_hier_out('pdus')
        if len(self.metadata_blocks) == 0:
            self.msg_connect((self.tagged_stream_to_pdu_block, 'pdus'), (self, 'pdus'))
        else:
            previous_block = self.tagged_stream_to_pdu_block
            for block in self.metadata_blocks:
                self.msg_connect((previous_block, 'pdus'), (block, 'pdus'))
                previous_block = block
            self.msg_connect((previous_block, 'pdus'), (self, 'pdus'))
