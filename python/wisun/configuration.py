# coding: utf-8
#
# Copyright (c) 2026 Gardena GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Support for Wi-SUN configuration parsing & representation."""

from collections import OrderedDict
from math import log2, floor

from .parameters import PHY_TYPES, PHY_MODES, WISUN_COUNTRY_CODES, WISUN_PHY_TYPES, WISUN_PHY_MODES_FSK, \
    WISUN_PHY_MODES_OFDM, WISUN_CHANNEL_PLANS, WISUN_FREQUENCY_BANDS, WISUN_SUPPORTED_PARAMETERS


class InvalidWiSunRegulatoryDomainException(Exception):
    """Unknown Wi-SUN regulatory domain."""


class InvalidWiSunPhyTypeException(Exception):
    """Invalid Wi-SUN PHY type."""


class InvalidWiSunPhyModeException(Exception):
    """Invalid Wi-SUN PHY mode."""


class InvalidWiSunChannelPlanException(Exception):
    """Invalid Wi-SUN channel plan."""


class InvalidWiSunParametersException(Exception):
    """Invalid combination of regulatory domain, channel plan ID & PHY type id."""


class UnsupportedWiSunPhyModeIdException(Exception):
    """Invalid Wi-SUN PHY mode ID for current regulatory domain & channel plan ID."""


class UnsupportedWiSunChannelException(Exception):
    """Channel not supported according to channel mask for current channel plan channel."""


def byte_length(x: int):
    """Return number of bytes required to represent given integer value."""
    return floor(log2(x) / 8) + 1


class ChannelMask:
    """Class representing a Wi-SUN channels mask."""

    def __init__(self, mask: int, length: int):
        """Initialize class from given mask."""
        self._mask = mask
        self._mask_length = int(length)

    @classmethod
    def from_string(cls, mask: str):
        """Parse Wi-SUN channel mask from string and return channel mask object.

        Note: Wi-SUN uses a weird mixed-Endianness format for the mask where the Endianness of the bytes is reversed to
        how it is written (least significant byte comes first), but the Endianness of the bits within a hexadecimal byte
        is as-written. This also means we must store the original mask as string, as leading zeros matter (e.g. "00:ff"
        is not the same as "ff"). Furthermore we need to remember the length of the channel mask to avoid considering
        any channels outside the mask as active.
        """
        mask = mask.replace(":", "")
        assert len(mask) % 2 == 0, "expected even number of hex digits"
        length = len(mask) / 2
        mask = int.from_bytes(reversed(bytes.fromhex(mask)))
        return cls(mask, length)

    def __contains__(self, channel: int):
        """Check if channel mask contains given channel (i.e. returns True if channel is enabled)."""
        channel_bit = 1 << channel
        if byte_length(channel_bit) > self._mask_length:
            return False
        return not channel_bit & self._mask

    def __str__(self):
        """Represent mask as string."""
        hexstr = f"{self._mask:0{self._mask_length * 2}x}"
        return ":".join(reversed([hexstr[i:i + 2] for i in range(0, len(hexstr), 2)]))

    def supported_channels(self):
        """Return list of all active channels in mask."""
        supported_channels = []
        for channel in range(self._mask_length * 8):
            if channel in self:
                supported_channels.append(channel)
        return supported_channels


class RadioConfiguration:
    """Represents radio configuration for Wi-SUN sniffer."""

    def __init__(self, modulation, modulation_index, symbol_rate,
                 channel_0_center_frequency, channel_spacing, channels):
        """Initialize class."""
        self.modulation = modulation
        self.modulation_index = modulation_index
        self.symbol_rate = symbol_rate
        self.channel_0_center_frequency = channel_0_center_frequency
        self.channel_spacing = channel_spacing
        self.channels = channels

    def __str__(self) -> str:
        """Represent all info as string."""
        s = f"{self.modulation}, mod. index: {self.modulation_index}, sym. rate: {self.symbol_rate / 1000:.1f} kHz, " \
            f"chan. 0 center freq.: {self.channel_0_center_frequency / 1e6:.2f} MHz, " \
            f"channel spacing: {self.channel_spacing / 1000:.1f} kHz, " \
            f"channels: {','.join([str(c) for c in self.channels])}"
        if self.is_valid_802154_phy_mode():
            s += " (802.15.4 PHY type / mode: %d / %d)" % self.get_802154_phy_type_mode()
        else:
            s += " (not a valid 802.15.4 PHY mode)"
        return s

    def info(self) -> OrderedDict:
        """Return info in human readable form as ordered dictionary."""
        if self.is_valid_802154_phy_mode():
            phy_mode_info = "%d / %d" % self.get_802154_phy_type_mode()
        else:
            phy_mode_info = "(not a valid 802.15.4 PHY mode)"
        if len(self.channels) <= 10:
            channels_str = f"{', '.join([str(c) for c in self.channels])}"
        else:
            channels_str = f"[{len(self.channels)} channels]"
        return OrderedDict([
            ("Modulation", self.modulation),
            ("Modulation index", f"{self.modulation_index:.1f}"),
            ("Symbol rate", f"{self.symbol_rate / 1000:.1f} kHz"),
            ("Channel 0 center frequency", f"{self.channel_0_center_frequency / 1e6:.1f} MHz"),
            ("Channel spacing", f"{self.channel_spacing / 1000:.1f} kHz"),
            ("Channels", channels_str),
            ("802.15.4 PHY type / mode", phy_mode_info),
        ])

    def bits_per_symbol(self) -> int:
        """Return number of bits per symbol."""
        if self.modulation == "2-FSK":
            return 1
        elif self.modulation == "4-FSK":
            return 2
        else:
            raise NotImplementedError()

    def data_rate(self) -> int:
        """Calculate data rate in bps."""
        return self.symbol_rate * self.bits_per_symbol()

    def channel_frequency(self, channel) -> int:
        """Calculate frequency for given channel in Hz."""
        return self.channel_0_center_frequency + channel * self.channel_spacing

    def is_valid_802154_phy_mode(self) -> bool:
        """Check if given configuration is a valid IEEE 802.15.4-2020 PHY mode."""
        return self.get_802154_phy_type_mode() is not None

    def get_802154_phy_type_mode(self) -> bool:
        """Get IEEE 802.15.4 PHY type & mode for current radio configuration."""
        desc = (self.data_rate(), self.modulation, self.modulation_index, self.channel_spacing)
        for t in PHY_TYPES.keys():
            if t in PHY_MODES.keys():
                for mode in PHY_MODES[t].keys():
                    if PHY_MODES[t][mode] == desc:
                        return (t, mode)
        return None


class WiSunConfiguration:
    """Represents Wi-SUN configuration."""

    def __init__(self, regulatory_domain: str, channel_plan_id: int, phy_mode_id: int,
                 allowed_channels: list[int] = []):
        """Initialize class from given parameters."""
        if regulatory_domain not in WISUN_COUNTRY_CODES.keys():
            raise InvalidWiSunRegulatoryDomainException("unknown regulatory domain: " + regulatory_domain)
        self.regulatory_domain = regulatory_domain
        if channel_plan_id not in WISUN_CHANNEL_PLANS.keys():
            raise InvalidWiSunChannelPlanException(f"invalid channel plan ID: {channel_plan_id}")
        self.channel_plan_id = channel_plan_id
        self.phy_mode_id = phy_mode_id
        if self.phy_type() not in WISUN_PHY_TYPES.keys():
            raise InvalidWiSunPhyTypeException(f"invalid Wi-SUN PHY type: {self.phy_type()}")
        if self.is_fsk() and self.phy_mode() not in WISUN_PHY_MODES_FSK.keys():
            raise InvalidWiSunPhyModeException(f"invalid Wi-SUN PHY mode for FSK: {self.phy_mode()}")
        if self.is_ofdm() and self.phy_mode() not in WISUN_PHY_MODES_OFDM.keys():
            raise InvalidWiSunPhyModeException(f"invalid Wi-SUN PHY mode for OFDM: {self.phy_mode()}")
        if (regulatory_domain, channel_plan_id) not in WISUN_SUPPORTED_PARAMETERS.keys():
            raise InvalidWiSunParametersException(f"channel plan ID {channel_plan_id} is not supported for "
                                                  f"regulatory domain {regulatory_domain}")
        num_chans, supported_phy_mode_ids, chan_mask = WISUN_SUPPORTED_PARAMETERS[(regulatory_domain, channel_plan_id)]
        self.number_of_channels = num_chans
        if self.phy_mode_id not in supported_phy_mode_ids:
            raise UnsupportedWiSunPhyModeIdException(f"PHY mode ID 0x{self.phy_mode_id:02x} is not supported for "
                                                     f"regulatory domain {regulatory_domain} and "
                                                     f"channel plan {channel_plan_id}")
        self.channel_mask = ChannelMask.from_string(chan_mask)
        for channel in allowed_channels:
            if channel not in self.channel_mask:
                raise UnsupportedWiSunChannelException(f"channel {channel} is not supported in channel mask for "
                                                       f"({regulatory_domain}, {channel_plan_id})")
        self.allowed_channels = allowed_channels

    def __str__(self) -> str:
        """Represent all info as string."""
        if len(self.allowed_channels) > 0:
            allowed = ",".join([str(c) for c in self.allowed_channels])
        else:
            allowed = "all"
        s = f"regulatory domain: {self.regulatory_domain}, channel plan ID: {self.channel_plan_id}, " \
            f"frequency band: {self.frequency_band()[0]:.1f} MHz – {self.frequency_band()[1]:.1f} MHz, " \
            f"PHY mode ID: 0x{self.phy_mode_id:02x}, number of channels: {self.number_of_channels}, " \
            f"allowed channels: {allowed}"
        return s

    def info(self) -> OrderedDict:
        """Return info in human readable form as ordered dictionary."""
        if len(self.allowed_channels) > 0:
            allowed = ", ".join([str(c) for c in self.allowed_channels])
        else:
            allowed = "all"
        return OrderedDict([
            ("Regulatory domain", self.regulatory_domain),
            ("Channel plan", str(self.channel_plan_id)),
            ("Frequency band", f"{self.frequency_band()[0]:.1f} MHz — {self.frequency_band()[1]:.1f} MHz"),
            ("PHY mode ID", f"0x{self.phy_mode_id:02x}"),
            ("Number of channels", str(self.number_of_channels)),
            ("Allowed channels", allowed),
        ])

    def phy_type(self) -> int:
        """Return Wi-SUN PHY type."""
        return self.phy_mode_id >> 4

    def phy_mode(self) -> int:
        """Return Wi-SUN PHY mode."""
        return self.phy_mode_id & 0xf

    def is_fsk(self) -> bool:
        """Check if configuration uses FSK modulation."""
        return self.phy_type() in {0, 1}

    def is_ofdm(self) -> bool:
        """Check if configuration uses OFDM modulation."""
        return self.phy_type() in {2, 3, 4, 5}

    def modulation(self) -> str:
        """Return modulation for current Wi-SUN configuration."""
        if self.is_fsk():
            return WISUN_PHY_MODES_FSK[self.phy_mode()][0]
        raise NotImplementedError

    def modulation_index(self) -> float:
        """Return modulation index for current Wi-SUN configuration."""
        if self.is_fsk():
            return WISUN_PHY_MODES_FSK[self.phy_mode()][2]
        raise NotImplementedError

    def symbol_rate(self) -> int:
        """Return symbol rate for current Wi-SUN configuration."""
        if self.is_fsk():
            return WISUN_PHY_MODES_FSK[self.phy_mode()][1]
        raise NotImplementedError

    def frequency_band(self) -> tuple[int]:
        """Return frequency band (tuple with lower and upper limit)."""
        return WISUN_FREQUENCY_BANDS[self.channel_plan_id]

    def channel_plan_name(self) -> str:
        """Return channel plan name for current Wi-SUN configuration."""
        return WISUN_CHANNEL_PLANS[self.channel_plan_id][0]

    def channel_spacing(self) -> int:
        """Return channel spacing for current Wi-SUN configuration."""
        return int(WISUN_CHANNEL_PLANS[self.channel_plan_id][1])

    def channel_0_center_frequency(self) -> int:
        """Return channel 0 center frequency for current Wi-SUN configuration."""
        return int(WISUN_CHANNEL_PLANS[self.channel_plan_id][2])

    def channels(self) -> list[int]:
        """Return list of all active channels."""
        if len(self.allowed_channels) > 0:
            return self.allowed_channels
        else:
            return self.channel_mask.supported_channels()

    def radio_configuration(self) -> RadioConfiguration:
        """Return RadioConfiguration instance for current Wi-SUN configuration."""
        return RadioConfiguration(self.modulation(), self.modulation_index(), self.symbol_rate(),
                                  self.channel_0_center_frequency(), self.channel_spacing(), self.channels())
