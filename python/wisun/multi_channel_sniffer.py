#
# Copyright (c) 2026 Gardena GmbH
# SPDX-License-Identifier: GPL-3.0-or-later

"""Flow graph receiving several Wi-SUN channels from an SDR.

This is the part the plain and the GUI multi-channel sniffer applications have in common,
which is everything except the plots.

Note that this module imports osmosdr and so is deliberately not imported by the package's
__init__: the rest of gr-wisun works, and its tests run, without gr-osmosdr installed.
"""

from collections import OrderedDict

import osmosdr
from gnuradio import blocks, gr, pdu, wisun

from .parameters import SUN_FSK_CHANNEL_PAGE, WISUN_FREQUENCY_BAND_802154_MAPPING
from .util import tabular_pretty_print


class MultiChannelSniffer(gr.top_block):
    """Receive several Wi-SUN channels at once and write the packets to a file.

    The sample rate, channel count and center frequency are derived from the channels the
    configuration asks for; see the comment below for how.

    The GUI sniffer builds on this and adds its plots, which is why the hardware source is
    an attribute rather than a local: it feeds the plots and the gain slider as well.
    """

    def __init__(self, device_string, gain, dest_file, wisun_config, **top_block_kwargs):
        """Build the flow graph for the given configuration."""
        gr.top_block.__init__(self, **top_block_kwargs)
        radio_config = wisun_config.radio_configuration()

        ##################################################
        # Variables
        ##################################################

        # Determine sample rate, number of channels & center frequency
        #
        # The strategy for this is as follows:
        # - determine highest & lowest channel
        # - add one channel at the top as channelizer will split one channel at the edge of the band
        # - determine number of channels (highest - lowest + 1)
        # - add one channel at the bottom if channel number is odd (we want an even number of channels)
        # - use lower middle channel for center frequency as we always have a buffer at the top, but not at the bottom
        # - calculate sample rate as number of channels * spacing
        #
        # See also https://wiki.gnuradio.org/index.php/Polyphase_Channelizer

        highest = max(radio_config.channels)
        lowest = min(radio_config.channels)
        highest += 1
        n_channels = highest - lowest + 1
        n_active_channels = len(radio_config.channels)
        if n_channels % 2 != 0:
            lowest -= 1
            n_channels += 1
        middle = int(lowest + n_channels / 2 - 1)
        # kept as attributes: the GUI sniffer labels its plots with them
        self.center_frequency = center_frequency = radio_config.channel_frequency(middle)
        self.sample_rate = sample_rate = n_channels * radio_config.channel_spacing
        print("Receiver configuration:")
        tabular_pretty_print(OrderedDict([
            ("Sample rate", f"{sample_rate / 1e6:.1f} MHz"),
            ("Frequency", f"{center_frequency / 1e6:.1f} MHz"),
            ("Gain", f"{gain}"),
            ("Number of PFB channels", f"{n_channels}"),
            ("Active channels", f"{n_active_channels}"),
            ("Lowest channel", f"{lowest}"),
            ("Middle channel", f"{middle}"),
            ("Highest channel", f"{highest}"),
        ]))

        metadata = {
            "packet-bit-rate": radio_config.data_rate(),
            "packet-channel-page": SUN_FSK_CHANNEL_PAGE,
            "packet-phy-band": WISUN_FREQUENCY_BAND_802154_MAPPING[wisun_config.channel_plan_id],
        }
        if radio_config.is_valid_802154_phy_mode():
            phy_type, phy_mode = radio_config.get_802154_phy_type_mode()
            metadata['packet-phy-type'] = phy_type
            metadata['packet-phy-mode'] = phy_mode

        ##################################################
        # Blocks
        ##################################################
        if device_string is None:
            self.osmosdr_source = osmosdr.source()
        else:
            self.osmosdr_source = osmosdr.source(device_string)
        self.osmosdr_source.set_sample_rate(sample_rate)
        self.osmosdr_source.set_center_freq(center_frequency, 0)
        self.osmosdr_source.set_gain_mode(False, 0)
        self.osmosdr_source.set_gain(gain, 0)
        self.osmosdr_source.set_if_gain(0, 0)
        self.osmosdr_source.set_bb_gain(0, 0)
        self.osmosdr_source.set_bandwidth(0, 0)

        multi_channel_receiver = wisun.multi_channel_receiver(sample_rate,
                                                              center_frequency,
                                                              radio_config.channel_0_center_frequency,
                                                              radio_config.channel_spacing,
                                                              radio_config.symbol_rate,
                                                              radio_config.channels,
                                                              fec=wisun_config.uses_fec(),
                                                              metadata=metadata)

        pdu_to_tagged_stream = pdu.pdu_to_tagged_stream(gr.types.byte_t, 'packet_len')
        file_sink = blocks.file_sink(gr.sizeof_char*1, dest_file, False)
        file_sink.set_unbuffered(True)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.osmosdr_source, 0), (multi_channel_receiver, 0))
        self.msg_connect((multi_channel_receiver, 'pdus'), (pdu_to_tagged_stream, 'pdus'))
        self.connect((pdu_to_tagged_stream, 0), (file_sink, 0))
