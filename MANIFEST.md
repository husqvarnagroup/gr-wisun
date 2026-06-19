# SPDX-FileCopyrightText: 2026 GARDENA GmbH
# SPDX-License-Identifier: GPL-3.0-or-later

title: gr-wisun
brief: Blocks for receiving Wi-SUN packets
tags:
  - wi-sun
  - wireshark
  - iot
  - ieee802.15.4
author:
  - Andreas Müller <andreas.mueller@husqvarnagroup.com>
copyright_owner:
  - GARDENA GmbH
dependencies:
  - gnuradio (>= 3.10.0)
#repo:
#website:
#icon:
gr_supported_version: v3.10
---

This out-of-tree module for GNU Radio provides basic blocks to support
Wi-SUN (more specifically the SUN FSK PHY specified in section 19 of
IEEE 802.15.4-2020). It allows sniffing Wi-SUN packets and feeding
them to Wireshark.

At the moment, this is mostly a proof-of-concept and comes with the
following limitations:
- only FSK modulation is supported (no OFDM)
- only receiving is supported (packet sending not implemented)
- performance is not optimized (in particular the clock
  synchronization could use more tuning)

That said, integration with Wireshark works well, and the sniffer is
fully functional.
