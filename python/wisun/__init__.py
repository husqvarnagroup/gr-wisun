# coding: utf-8
#
# Copyright 2008,2009 Free Software Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

# The presence of this file turns this directory into a Python package

"""This is the GNU Radio WISUN module. Place your Python package description here (python/__init__.py)."""

# import pybind11 generated symbols into the wisun namespace
try:
    # this might fail if the module is python-only
    from .wisun_python import *  # noqa
except ModuleNotFoundError:
    pass

# import any pure python here
try:
    from .baseband_channel_receiver import baseband_channel_receiver  # noqa
    from .single_channel_receiver import single_channel_receiver  # noqa
except ImportError as e:
    # allow pytest to run without installed gr-wisun (blocks are not needed for Python-only tests)
    import os
    if os.environ.get('PYTEST_VERSION'):
        pass
    else:
        raise e
#
