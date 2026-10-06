#!/usr/bin/env python
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

# Oversampling of the channelizer's outputs, as a factor on the normal output rate of
# channel spacing. Without it the samples per symbol of every Wi-SUN FSK mode comes out as
# channel spacing over symbol rate, which is 2 for every mode in every regulatory domain -
# the lowest rate the chain can work at, and one the single-channel tests already document
# as unreliable for coded frames. The discriminator is a nonlinearity and the symbol
# synchronizer interpolates, and neither has room at 2 samples per symbol: measured over one
# wideband recording, interpolating a channel up without adding any information recovers
# packets that 2 samples per symbol loses, which is what identifies this rather than the
# channelizer's filtering as the limit.
#
# The cost is the per-channel chains running this much faster. The channelizer itself is
# unaffected; its taps are designed at the input rate either way.
DEFAULT_OVERSAMPLING = 2


class multi_channel_receiver(gr.hier_block2):
    """Block to receive Wi-SUN packets from multiple channels using polyphase channelizer."""

    def __init__(self, sample_rate, center_frequency, channel_0_frequency, channel_spacing, symbol_rate, channels,
                 fec=False, metadata=None, channels_outside_mask=None, oversampling=DEFAULT_OVERSAMPLING):
        """Initialize block.

        `oversampling` multiplies the samples per symbol the channel receivers work at; see
        DEFAULT_OVERSAMPLING for why it is not 1. The channelizer requires it to divide the
        number of channels.
        """
        gr.hier_block2.__init__(self,
                                "multi_channel_receiver",
                                gr.io_signature(1, 1, gr.sizeof_gr_complex),  # Input signature
                                gr.io_signature(0, 0, 0))  # Output signature

        channels = set(channels)
        # channels received although the regulatory channel mask excludes them; packets on
        # them are real but unexpected, so the channel receiver reports them as warnings
        channels_outside_mask = set() if channels_outside_mask is None else set(channels_outside_mask)
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
        # the channelizer accepts an oversampling of n_channels / i only
        assert n_channels % oversampling == 0, "oversampling must divide the number of channels"
        samples_per_symbol = oversampling * sample_rate / n_channels / symbol_rate
        assert samples_per_symbol % 1 == 0, "samples_per_symbol must be an integer"
        samples_per_symbol = int(samples_per_symbol)
        # kept as attributes: what the channel receivers work at, which is what the
        # oversampling is for
        self.oversampling = oversampling
        self.samples_per_symbol = samples_per_symbol
        filter_bandwidth = channel_spacing / 2 * 0.8
        filter_transition = channel_spacing / 2 * 0.2
        tabular_pretty_print(OrderedDict([
            ("Number of PFB channels", f"{n_channels}"),
            ("Active channels", f"{n_active_channels}"),
            ("Oversampling", f"{oversampling}"),
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
            oversample_rate=oversampling,
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
                      ("active -> setting up channel receiver"
                       + (" (outside the regulatory channel mask)"
                          if wisun_channel in channels_outside_mask else "")
                       if in_use else "not active -> connecting to null sink"))
            if in_use:
                covered_channels.add(wisun_channel)
                metadata["packet-channel-number"] = wisun_channel
                baseband_channel_receiver = wisun.baseband_channel_receiver(
                    samples_per_symbol,
                    fec=fec,
                    gated_power_squelch=True,
                    metadata=metadata,
                    outside_channel_mask=wisun_channel in channels_outside_mask)
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
