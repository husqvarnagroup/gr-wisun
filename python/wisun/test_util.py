# coding: utf-8
#
# Copyright (c) 2026 Gardena GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pytest tests for functions from util module."""

import pytest

from .util import pfb_channel_to_frequency, frequency_to_wisun_channel


@pytest.mark.parametrize('channel,n_channels,center_frequency,channel_spacing,expected_frequency', [
    # values from example in GNU Radio wiki (https://wiki.gnuradio.org/index.php/Polyphase_Channelizer):
    (0, 12, 90.9e6, 0.2e6, 90.9e6),
    (1, 12, 90.9e6, 0.2e6, 91.1e6),
    (2, 12, 90.9e6, 0.2e6, 91.3e6),
    (3, 12, 90.9e6, 0.2e6, 91.5e6),
    (4, 12, 90.9e6, 0.2e6, 91.7e6),
    (5, 12, 90.9e6, 0.2e6, 91.9e6),
    (6, 12, 90.9e6, 0.2e6, None),
    (7, 12, 90.9e6, 0.2e6, 89.9e6),
    (8, 12, 90.9e6, 0.2e6, 90.1e6),
    (9, 12, 90.9e6, 0.2e6, 90.3e6),
    (10, 12, 90.9e6, 0.2e6, 90.5e6),
    (11, 12, 90.9e6, 0.2e6, 90.7e6),
    # example with odd number of channels
    (0, 5, 100e6, 0.1e6, 100.0e6),
    (1, 5, 100e6, 0.1e6, 100.1e6),
    (2, 5, 100e6, 0.1e6, 100.2e6),
    (3, 5, 100e6, 0.1e6, 99.8e6),
    (4, 5, 100e6, 0.1e6, 99.9e6),
])
def test_pfb_channel_to_frequency(channel, n_channels, center_frequency, channel_spacing, expected_frequency):
    assert pfb_channel_to_frequency(channel, n_channels, center_frequency, channel_spacing) == expected_frequency


@pytest.mark.parametrize('frequency,channel_0_frequency,channel_spacing,expected_channel', [
    (None, 863.1e6, 0.1e6, None),
    (863.0e6, 863.1e6, 0.1e6, None),
    (863.1e6, 863.1e6, 0.1e6, 0),
    (863.2e6, 863.1e6, 0.1e6, 1),
    (863.15e6, 863.1e6, 0.1e6, None),
])
def test_frequency_to_wisun_channel(frequency, channel_0_frequency, channel_spacing, expected_channel):
    assert frequency_to_wisun_channel(frequency, channel_0_frequency, channel_spacing) == expected_channel
