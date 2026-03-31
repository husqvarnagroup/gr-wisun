
# coding: utf-8
#
# Copyright (c) 2026 Gardena GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Pytest tests for functions in parameters.py.
"""

import pytest

from .configuration import byte_length, ChannelMask
from .parameters import WISUN_SUPPORTED_PARAMETERS


@pytest.mark.parametrize('x,expected_length', [
    (1, 1),
    (255, 1),
    (256, 2),
    (0xfff, 2),
    (0x10000, 3),
])
def test_byte_length(x, expected_length):
    """Test for byte_length() function."""
    assert byte_length(x) == expected_length


@pytest.mark.parametrize('mask_string,channel,active', [
    ("ff:01:00:00:c0", 0, False),
    ("ff:01:00:00:c0", 1, False),
    ("ff:01:00:00:c0", 8, False),
    ("ff:01:00:00:c0", 9, True),
    ("ff:01:00:00:c0", 20, True),
    ("ff:01:00:00:c0", 37, True),
    ("ff:01:00:00:c0", 38, False),
    ("ff:01:00:00:c0", 39, False),
    ("ff:01:00:00:c0", 40, False),
    ("ff:01:00:00:c0", 100, False),
])
def test_channel_mask(mask_string, channel, active):
    """Test for ChannelMask class based on example from specification."""
    mask = ChannelMask.from_string(mask_string)
    assert (channel in mask) == active


@pytest.mark.parametrize('mask_string', [
    "00",
    "00:a1",
    "bc:00",
    "00:a1:b2",
    "12:34:00",
    "00:00:00:01"
])
def test_channel_mask_string_representation(mask_string):
    """Test for ChannelMask class string representation (should be same as original except for upper/lower-case)."""
    mask = ChannelMask.from_string(mask_string)
    assert str(mask) == mask_string


@pytest.mark.parametrize("num_channels,phy_mode_ids,mask", WISUN_SUPPORTED_PARAMETERS.values())
def test_supported_parameters_consistency(num_channels, phy_mode_ids, mask):
    """Test to make sure channel masks in supported parameters table have expected number of channels."""
    mask = ChannelMask.from_string(mask)
    assert num_channels == len(mask.supported_channels())
