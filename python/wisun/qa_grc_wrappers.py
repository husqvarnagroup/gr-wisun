#!/usr/bin/env python
#
# Copyright 2026 GARDENA GmbH.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Tests that each GRC wrapper passes its parameters to the argument of the same name.

Nothing else checks this: a flow graph built in GRC only shows the mistake as behaviour,
and a parameter added to a constructor ahead of an existing one silently shifts every
positional argument after it. Limited to the hierarchical blocks, the ones with enough
parameters and defaults for that to happen - the C++ blocks are pybind-wrapped and carry no
introspectable signature.
"""

import inspect
import os
import re

import yaml
from gnuradio import gr_unittest

try:
    from gnuradio import wisun
except ImportError:
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from gnuradio import wisun

GRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'grc')
HIER_BLOCKS = ('baseband_channel_receiver', 'single_channel_receiver', 'multi_channel_receiver')


def make_arguments(template):
    """Split a GRC make template into its (keyword, parameter id) arguments."""
    inside = template[template.index('(') + 1:template.rindex(')')]
    arguments = []
    for argument in inside.split(','):
        argument = argument.strip()
        if not argument:
            continue
        keyword, _, value = argument.rpartition('=')
        match = re.fullmatch(r'\$\{(\w+)\}', value.strip())
        assert match, f"unexpected argument {argument!r}"
        arguments.append((keyword.strip() or None, match.group(1)))
    return arguments


class qa_grc_wrappers(gr_unittest.TestCase):
    """Tests for the GRC block definitions."""

    def test_001_parameters_reach_the_argument_of_the_same_name(self):
        """Every GRC parameter must bind to the constructor argument it is named after."""
        for block in HIER_BLOCKS:
            path = os.path.join(GRC_DIR, f'wisun_{block}.block.yml')
            with open(path) as definition:
                grc = yaml.safe_load(definition)
            declared = {parameter['id'] for parameter in grc['parameters']}
            arguments = make_arguments(grc['templates']['make'])

            positional = [name for keyword, name in arguments if keyword is None]
            keywords = {keyword: name for keyword, name in arguments if keyword is not None}
            for _, name in arguments:
                self.assertIn(name, declared, f"{block}: {name} is not a GRC parameter")

            signature = inspect.signature(getattr(wisun, block).__init__)
            bound = signature.bind('self', *positional, **keywords)
            for argument, value in bound.arguments.items():
                if argument == 'self':
                    continue
                self.assertEqual(argument, value,
                                 f"{block}: GRC parameter {value} is passed as {argument}")


if __name__ == '__main__':
    gr_unittest.run(qa_grc_wrappers)
