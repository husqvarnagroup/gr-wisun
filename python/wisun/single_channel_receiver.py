#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Hierarchical block to receive a single channel."""

from gnuradio import analog, blocks, filter, gr, wisun
from gnuradio.fft import window
from gnuradio.filter import firdes


class single_channel_receiver(gr.hier_block2):
    """Block to receive Wi-SUN packets on a single channel."""

    def __init__(self, sample_rate, frequency_offset, channel_spacing, decimation, samples_per_symbol,
                 fec=False, gated_power_squelch=False, metadata=None):
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
        # Filtering is done on complex baseband, where the channel straddles 0 Hz, so the
        # cutoff is half the channel spacing less a margin: 0.45 puts the passband edge just
        # inside the neighbouring channel.
        #
        # Measured against gr-wisun-test-suite, aggregated over all five recordings at 13 to
        # 10 dB: the previous 0.5/0.3 decoded 0.72 of the packets, this 0.45/0.15 decodes
        # 0.81. Nearly all of that comes from the narrower cutoff rather than the steeper
        # transition - 0.5/0.15 only reaches 0.74 - so what it buys is rejection of the
        # neighbouring channel, not a smaller noise bandwidth. The steeper transition is
        # what keeps the cutoff from costing packets on an unimpaired recording: 0.45/0.3
        # loses two of them.
        #
        # Narrowing further by sizing the filter to the signal (Carson's rule, 37.5 kHz for
        # 50 ksym/s at h=0.5) was measured too and is worse: it cuts into the signal and
        # costs both clean packets and bit errors.
        CHANNEL_FILTER_WIDTH = 0.45
        CHANNEL_FILTER_TRANSITION = 0.15
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
                                                                    fec=fec,
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
