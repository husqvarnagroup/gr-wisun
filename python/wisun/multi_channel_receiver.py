#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#



from gnuradio import gr

class multi_channel_receiver(gr.hier_block2):
    """
    docstring for block multi_channel_receiver
    """
    def __init__(self, sample_rate, center_frequency, channel_0_frequency, channel_spacing, symbol_rate, channels, metadata=None):
        gr.hier_block2.__init__(self,
            "multi_channel_receiver",
            gr.io_signature(<+MIN_IN+>, <+MAX_IN+>, gr.sizeof_<+ITYPE+>),  # Input signature
            gr.io_signature(<+MIN_OUT+>, <+MAX_OUT+>, gr.sizeof_<+OTYPE+>)) # Output signature

        # Define blocks and connect them
        self.connect()
