# coding: utf-8
#
# Copyright (c) 2026 Gardena GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Collection of utility functions."""


def tabular_pretty_print(data):
    """Pretty print key/value data from dict as table."""
    width1 = max([len(key) for key in data.keys()])
    width2 = max([len(data[key]) for key in data.keys()])
    print(f"┌─{'─'*width1}─┬─{'─'*width2}─┐")
    for key in data.keys():
        print(f"│ {key:{width1}s} │ {data[key]:{width2}s} │")
    print(f"└─{'─'*width1}─┴─{'─'*width2}─┘")


def pfb_channel_to_frequency(channel, n_channels, center_frequency, channel_spacing):
    """Convert given channel from polyphase channelizer to frequency.

    @return Frequency of channel in Hz, None if channel is the split channel.

    See https://wiki.gnuradio.org/index.php/Polyphase_Channelizer
    """
    assert channel >= 0 and channel < n_channels, "invalid channel"
    if channel == n_channels / 2:
        return None  # channel in the middle is split if channel number is even
    elif channel < n_channels / 2:
        return center_frequency + channel_spacing * channel
    else:
        return center_frequency - channel_spacing * (n_channels - channel)


def frequency_to_wisun_channel(frequency, channel_0_frequency, channel_spacing):
    """Convert given frequency to Wi-SUN channel.

    @return Wi-SUN channel or None if frequency is not associated with a Wi-SUN channel.
    """
    if frequency is None:
        return None
    if frequency < channel_0_frequency:
        return None
    offset = frequency - channel_0_frequency
    if offset % channel_spacing == 0:
        return int(offset / channel_spacing)
    return None
