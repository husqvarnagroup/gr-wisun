#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Hierarchical block to receive a single channel."""

from gnuradio import analog, blocks, filter, gr
from gnuradio.fft import window
from gnuradio.filter import firdes
from gnuradio import wisun


class single_channel_receiver(gr.hier_block2):
    """Block to receive Wi-SUN packets on a single channel."""

    def __init__(self, sample_rate, frequency_offset, channel_spacing, decimation, samples_per_symbol,
                 gated_power_squelch=False, metadata=None):
        """Initialize block."""
        gr.hier_block2.__init__(self,
                                "single_channel_receiver",
                                gr.io_signature(1, 1, gr.sizeof_gr_complex),  # Input signature
                                gr.io_signature(0, 0, 0))  # Output signature

        ##################################################
        # Checks
        ##################################################
        assert sample_rate >= channel_spacing, "sampling bandwidth does not cover full channel"
        assert abs(frequency_offset) + channel_spacing / 2 <= sample_rate / 2, "channel not fully in sampled band"

        ##################################################
        # Blocks
        ##################################################
        if frequency_offset != 0:
            sig_source = analog.sig_source_c(sample_rate, analog.GR_COS_WAVE, -frequency_offset, 1, 0, 0)
            multiply = blocks.multiply_vcc(1)
        # Note: The filter width should be a bit smaller than the channel spacing (e.g. 0.9 * channel spacing). Since
        # the filtering is done on complex baseband, the signal bandwidth must be divided by 2 to get the cutoff
        # frequency for the low-pass filter (signal is centered around 0, half on negative side, half on positive), so
        # we could e.g. use 0.45 * channel spacing. However, we have not yet done any frequency correction here and
        # experimentally, a higher cutoff frequency seems to work better.
        CHANNEL_FILTER_WIDTH = 0.5
        CHANNEL_FILTER_TRANSITION = 0.2
        low_pass_filter = filter.fir_filter_ccf(
            decimation,
            firdes.low_pass(
                1,
                sample_rate,
                CHANNEL_FILTER_WIDTH * channel_spacing,
                CHANNEL_FILTER_TRANSITION * channel_spacing,
                window.WIN_HAMMING,
                6.76))
        baseband_channel_receiver = wisun.baseband_channel_receiver(samples_per_symbol,
                                                                    gated_power_squelch=gated_power_squelch,
                                                                    metadata=metadata)

        ##################################################
        # Connections
        ##################################################
        if frequency_offset != 0:
            self.connect((self, 0), (multiply, 0))
            self.connect((sig_source, 0), (multiply, 1))
            self.connect((multiply, 0), (low_pass_filter, 0))
        else:
            self.connect((self, 0), (low_pass_filter, 0))
        self.connect((low_pass_filter, 0), (baseband_channel_receiver, 0))
        self.message_port_register_hier_out('pdus')
        self.msg_connect((baseband_channel_receiver, 'pdus'), (self, 'pdus'))
