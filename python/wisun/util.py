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
