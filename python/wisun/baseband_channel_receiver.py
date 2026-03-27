#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#



from gnuradio import gr

class baseband_channel_receiver(gr.hier_block2):
    """
    docstring for block baseband_channel_receiver
    """
    def __init__(self, samples_per_symbol, metadata):
        gr.hier_block2.__init__(self,
            "baseband_channel_receiver",
            gr.io_signature(<+MIN_IN+>, <+MAX_IN+>, gr.sizeof_<+ITYPE+>),  # Input signature
            gr.io_signature(<+MIN_OUT+>, <+MAX_OUT+>, gr.sizeof_<+OTYPE+>)) # Output signature

        # Define blocks and connect them
        self.connect()
