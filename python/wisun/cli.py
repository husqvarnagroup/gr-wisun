#
# Copyright (c) 2026 Gardena GmbH
# SPDX-License-Identifier: GPL-3.0-or-later

"""Command line handling shared by the sniffer applications.

All four applications take the same receiver and output options, offer the same
`--list-*` options, write to the same kind of FIFO and are shut down the same way. This
holds the one copy of each of those, so that adding a regulatory domain or a PHY mode does
not mean editing four listings that have to agree.
"""

import contextlib
import os
import signal
import stat
import sys

from .configuration import (
    InvalidWiSunChannelPlanException,
    InvalidWiSunParametersException,
    InvalidWiSunPhyModeException,
    InvalidWiSunPhyTypeException,
    InvalidWiSunRegulatoryDomainException,
    UnsupportedWiSunChannelException,
    UnsupportedWiSunPhyModeIdException,
    WiSunConfiguration,
)
from .multi_channel_receiver import DEFAULT_OVERSAMPLING
from .parameters import (
    WISUN_CHANNEL_PLANS,
    WISUN_COUNTRY_CODES,
    WISUN_FREQUENCY_BANDS,
    WISUN_PHY_MODES_FSK,
    WISUN_PHY_TYPES,
)
from .util import tabular_pretty_print

# every way WiSunConfiguration can reject what was asked for
CONFIGURATION_EXCEPTIONS = (
    InvalidWiSunChannelPlanException,
    InvalidWiSunParametersException,
    InvalidWiSunPhyModeException,
    InvalidWiSunPhyTypeException,
    InvalidWiSunRegulatoryDomainException,
    UnsupportedWiSunChannelException,
    UnsupportedWiSunPhyModeIdException,
)


def add_receiver_arguments(parser):
    """Add the SDR and output options every application takes."""
    parser.add_argument('--device', type=str, default=None,
                        help="OsmoSDR device string (leave empty if only one SDR connected)")
    parser.add_argument('--gain', type=int, default=30, help="SDR hardware RX gain [dB]")
    parser.add_argument('--dest-file', type=str, default="/tmp/gr-wisun-sniffer", help="Output file (FIFO)")


def add_mode_arguments(parser):
    """Add the options selecting one Wi-SUN mode.

    Not used by the multi-mode sniffer, which takes a list of modes instead.
    """
    parser.add_argument('-r', '--regulatory-domain', type=str, default="EU", help="Wi-SUN regulatory domain")
    parser.add_argument('-p', '--channel-plan', type=int, default=32, help="Wi-SUN channel plan ID")
    parser.add_argument('-t', '--phy-type', type=int, default=0, help="Wi-SUN PHY type")
    parser.add_argument('-m', '--phy-mode', type=int, default=1, help="Wi-SUN PHY mode")


def add_oversampling_argument(parser):
    """Add the option choosing the channelizer's oversampling.

    Only the multi-channel applications take it; it is what sets the samples per symbol the
    channel receivers work at.
    """
    parser.add_argument('--oversampling', type=int, default=DEFAULT_OVERSAMPLING,
                        help="Channelizer oversampling; multiplies the samples per symbol the "
                             "channel receivers work at, and the CPU they need. Must divide the "
                             "number of channelizer channels")


def add_channel_mask_argument(parser):
    """Add the option restricting reception to the regulatory channel mask.

    Every application takes it, including the multi-mode sniffer, which does not use
    `add_mode_arguments`.
    """
    parser.add_argument('--mask-channels-only', action="store_true",
                        help="Receive only the channels the regulatory channel mask allows "
                             "(default: every channel of the channel plan)")


def add_list_arguments(parser):
    """Add the options that print a table of Wi-SUN parameters and exit."""
    parser.add_argument('--list-regulatory-domains', action="store_true",
                        help="List Wi-SUN regulatory domains & exit")
    parser.add_argument('--list-channel-plans', action="store_true",
                        help="List Wi-SUN channel plans & exit")
    parser.add_argument('--list-phy-types', action="store_true",
                        help="List Wi-SUN PHY types (first 4 bits of PHY mode ID) & exit")
    parser.add_argument('--list-phy-modes', action="store_true",
                        help="List Wi-SUN PHY modes for FSK (second 4 bits of PHY mode ID) & exit")


def handle_list_arguments(args):
    """Print whichever listing was asked for and exit; return if none was."""
    if args.list_regulatory_domains:
        for country in sorted(WISUN_COUNTRY_CODES.keys()):
            print(f"{country}: {WISUN_COUNTRY_CODES[country]}")
        sys.exit(0)

    if args.list_channel_plans:
        print("ID\tName\t\tFrequency band\t\tChannel spacing")
        print('-' * 80)
        for id_ in sorted(WISUN_CHANNEL_PLANS.keys()):
            name, spacing, _ = WISUN_CHANNEL_PLANS[id_]
            band = WISUN_FREQUENCY_BANDS[id_]
            print(f"{id_}\t{name}\t{band[0]:.1f} - {band[1]:.1f} MHz\t{spacing / 1000:.0f} kHz")
        sys.exit(0)

    if args.list_phy_types:
        for id_ in sorted(WISUN_PHY_TYPES.keys()):
            print(f"{id_}: {WISUN_PHY_TYPES[id_]}")
        sys.exit(0)

    if args.list_phy_modes:
        print("ID  Modulation  Symbol rate  Modulation Index")
        print("-" * 80)
        for id_ in sorted(WISUN_PHY_MODES_FSK.keys()):
            modulation, symbol_rate, modulation_index, _ = WISUN_PHY_MODES_FSK[id_]
            print(f"{id_}   {modulation}       {symbol_rate / 1000:3.0f} kbps     {modulation_index:.1f}")
        sys.exit(0)


def ensure_fifo(path):
    """Make sure the output path is a FIFO, creating it if it does not exist.

    Exits with an error if something else is already there, since writing packets into a
    regular file of that name is not what the caller asked for.
    """
    if os.path.exists(path):
        if not stat.S_ISFIFO(os.stat(path).st_mode):
            sys.stderr.write(f"ERROR: file '{path}' exists, but is not a FIFO\n")
            sys.exit(1)
    else:
        os.mkfifo(path)


def build_configuration(regulatory_domain, channel_plan_id, phy_mode_id, allowed_channels=None,
                        mask_channels_only=False, label=""):
    """Build a Wi-SUN configuration, reporting anything wrong with it and exiting.

    Returns the configuration. OFDM modes are rejected here: they parse and describe
    themselves perfectly well, but nothing in this module can receive them.

    `label` is appended to the headings of the printed tables, for the multi-mode sniffer
    which builds several configurations and has to say which is which.
    """
    try:
        config = WiSunConfiguration(regulatory_domain=regulatory_domain,
                                    channel_plan_id=channel_plan_id,
                                    phy_mode_id=phy_mode_id,
                                    allowed_channels=allowed_channels,
                                    mask_channels_only=mask_channels_only)
    except CONFIGURATION_EXCEPTIONS as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)

    print(f"WiSUN configuration{label}:")
    tabular_pretty_print(config.info())
    if config.channels_outside_mask():
        outside = ", ".join(str(channel) for channel in config.channels_outside_mask())
        sys.stderr.write(f"WARNING: receiving channels the regulatory channel mask excludes: {outside}\n"
                         "         (pass --mask-channels-only to skip them)\n")
    print(f"Radio configuration{label}:")
    tabular_pretty_print(config.radio_configuration().info())

    if config.is_ofdm():
        sys.stderr.write("ERROR: OFDM modes are not (yet) supported.\n")
        sys.exit(1)

    return config


def run_until_interrupted(flow_graph, after_start=None):
    """Run a flow graph until Enter is pressed or a termination signal arrives.

    `after_start` is called once the flow graph is running, for anything that can only be
    asked of a started graph.
    """
    def handle_signal(sig=None, frame=None):
        flow_graph.stop()
        flow_graph.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    flow_graph.start()
    if after_start is not None:
        after_start()
    with contextlib.suppress(EOFError):
        input('Press Enter to quit:\n')
    flow_graph.stop()
    flow_graph.wait()
