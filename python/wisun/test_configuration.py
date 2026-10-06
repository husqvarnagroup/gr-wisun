#
# Copyright (c) 2026 Gardena GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pytest tests for functions in parameters.py."""

import pytest

from .configuration import (
    ChannelMask,
    UnsupportedWiSunChannelException,
    WiSunConfiguration,
    byte_length,
)
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


@pytest.mark.parametrize('domain,plan', sorted(WISUN_SUPPORTED_PARAMETERS.keys()))
def test_plan_channels_leave_valid_total_num_chan(domain, plan):
    """The mask must leave exactly ValidTotalNumChan of the plan's channels.

    `plan_channels()` derives the channel space, because [Wi-SUN] Table 8 gives only the
    count after masking. This checks the derivation against that count for every supported
    combination, which is what keeps it honest - a wrong channel space, or a misread mask,
    shows up here.
    """
    valid_total_num_chan, phy_mode_ids, _ = WISUN_SUPPORTED_PARAMETERS[(domain, plan)]
    config = WiSunConfiguration(domain, plan, sorted(phy_mode_ids)[0])
    assert len(config.mask_channels()) == valid_total_num_chan


def test_eu_plan_33_channels():
    """EU channel plan 33 holds 35 channels, 29 of them allowed by the regulatory mask.

    35 is also IEEE 802.15.4's TotalNumChan for 863-870 MHz at 200 kHz spacing, and 29 is
    [Wi-SUN] Table 8's ValidTotalNumChan, so both ends of the derivation are pinned here.
    """
    config = WiSunConfiguration("EU", 33, 0x13)
    assert len(config.plan_channels()) == 35
    assert config.plan_channels()[-1] == 34
    assert len(config.mask_channels()) == 29
    assert config.channels_outside_mask() == [27, 28, 30, 31, 32, 33]


def test_channels_outside_the_mask_are_received_by_default():
    """Devices have been seen transmitting outside the mask, so those channels are received.

    A sniffer that skips them cannot report them at all, which is why this is the default
    rather than an option.
    """
    assert WiSunConfiguration("EU", 33, 0x13).channels() == list(range(35))


def test_mask_channels_only_restricts_to_the_mask():
    """With `mask_channels_only` nothing outside the regulatory mask is received."""
    config = WiSunConfiguration("EU", 33, 0x13, mask_channels_only=True)
    assert config.channels() == config.mask_channels()
    assert config.channels_outside_mask() == []
    assert 30 not in config.channels()


def test_a_channel_outside_the_mask_can_be_asked_for():
    """Asking for a mask-excluded channel is allowed, so it can be sniffed deliberately."""
    assert WiSunConfiguration("EU", 33, 0x13, allowed_channels=[30]).channels() == [30]
    assert WiSunConfiguration("EU", 33, 0x13, allowed_channels=[30]).channels_outside_mask() == [30]


def test_a_channel_outside_the_mask_is_refused_with_mask_channels_only():
    """With `mask_channels_only` a mask-excluded channel is an error, as it used to be."""
    with pytest.raises(UnsupportedWiSunChannelException):
        WiSunConfiguration("EU", 33, 0x13, allowed_channels=[30], mask_channels_only=True)


def test_a_channel_outside_the_plan_is_refused():
    """A channel the plan does not define is an error whatever the mask says."""
    with pytest.raises(UnsupportedWiSunChannelException):
        WiSunConfiguration("EU", 33, 0x13, allowed_channels=[35])
