#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Hierarchical block to receive multiple Wi-SUN channels simultaneously."""

from collections import OrderedDict

from gnuradio import blocks, gr, wisun
from gnuradio.fft import window
from gnuradio.filter import firdes, pfb
from gnuradio.wisun.util import frequency_to_wisun_channel, pfb_channel_to_frequency, tabular_pretty_print

OVERSAMPLING = 1


class multi_channel_receiver(gr.hier_block2):
    """Block to receive Wi-SUN packets from multiple channels using polyphase channelizer."""

    def __init__(self, sample_rate, center_frequency, channel_0_frequency, channel_spacing, symbol_rate, channels,
                 metadata=None):
        """Initialize block."""
        gr.hier_block2.__init__(self,
                                "multi_channel_receiver",
                                gr.io_signature(1, 1, gr.sizeof_gr_complex),  # Input signature
                                gr.io_signature(0, 0, 0))  # Output signature

        channels = set(channels)
        if metadata is None:
            metadata = {}

        ##################################################
        # Checks
        ##################################################
        assert sample_rate % channel_spacing == 0, "sample rate must be an integer multiple of channel spacing"
        assert (channel_0_frequency - center_frequency) % channel_spacing == 0, \
            "channel 0 frequency offset from center frequency must be an integer multiple of channel spacing"
        assert channel_spacing % symbol_rate == 0, "channel spacing must be an integer multiple of symbol rate"

        ##################################################
        # Calculations
        ##################################################
        n_channels = int(sample_rate / channel_spacing)
        n_active_channels = len(channels)
        samples_per_symbol = sample_rate / n_channels / symbol_rate
        assert samples_per_symbol % 1 == 0, "samples_per_symbol must be an integer"
        samples_per_symbol = int(samples_per_symbol)
        filter_bandwidth = channel_spacing / 2 * 0.8
        filter_transition = channel_spacing / 2 * 0.2
        tabular_pretty_print(OrderedDict([
            ("Number of PFB channels", f"{n_channels}"),
            ("Active channels", f"{n_active_channels}"),
            ("Oversampling", f"{OVERSAMPLING}"),
            ("Samples per symbol", f"{samples_per_symbol}"),
            ("PFB channel filter bandwidth", f"{filter_bandwidth/1e3:.1f} kHz"),
            ("PFB channel filter transition", f"{filter_transition/1e3:.1f} kHz"),
        ]))

        ##################################################
        # Blocks & Connections
        ##################################################
        pfb_channelizer = pfb.channelizer_ccf(
            numchans=n_channels,
            taps=firdes.low_pass(
                1,
                sample_rate,
                filter_bandwidth,
                filter_transition,
                window.WIN_HAMMING,
                6.76),
            oversample_rate=OVERSAMPLING,
            atten=100
        )
        self.connect((self, 0), (pfb_channelizer, 0))
        self.message_port_register_hier_out('pdus')

        covered_channels = set()
        for pfb_channel in range(n_channels):
            channel_frequency = pfb_channel_to_frequency(pfb_channel, n_channels, center_frequency, channel_spacing)
            wisun_channel = frequency_to_wisun_channel(channel_frequency, channel_0_frequency, channel_spacing)
            in_use = wisun_channel in channels
            if channel_frequency is None:
                print(f"PFB channel {pfb_channel:2}/{n_channels}: no associated frequency -> connecting to null sink")
            elif wisun_channel is None:
                print(f"PFB channel {pfb_channel:2}/{n_channels} ({channel_frequency/1e6:.1f} MHz): no associated " +
                      "Wi-SUN channel -> connecting to null sink")
            else:
                print(f"PFB channel {pfb_channel:2}/{n_channels} ({channel_frequency/1e6:.1f} MHz): " +
                      f"Wi-SUN channel {wisun_channel:2}; " +
                      ("active -> setting up channel receiver" if in_use else "not active -> connecting to null sink"))
            if in_use:
                covered_channels.add(wisun_channel)
                metadata["packet-channel-number"] = wisun_channel
                baseband_channel_receiver = wisun.baseband_channel_receiver(samples_per_symbol,
                                                                            gated_power_squelch=True,
                                                                            metadata=metadata)
                add_pcap_hdr = wisun.pdu_add_pcapng_header(True, True, True)
                self.connect((pfb_channelizer, pfb_channel), (baseband_channel_receiver, 0))
                self.msg_connect((baseband_channel_receiver, 'pdus'), (add_pcap_hdr, 'pdus'))
                self.msg_connect((add_pcap_hdr, 'pdus'), (self, 'pdus'))
            else:
                null_sink = blocks.null_sink(gr.sizeof_gr_complex)
                self.connect((pfb_channelizer, pfb_channel), null_sink)

        # make sure all channels are covered
        assert channels == covered_channels, \
            f"the following active channels are not covered: {channels - covered_channels}"
