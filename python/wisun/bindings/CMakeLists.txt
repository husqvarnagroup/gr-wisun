# Copyright 2020 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

########################################################################
# Check if there is C++ code at all
########################################################################
if(NOT wisun_sources)
    message(STATUS "No C++ sources... skipping python bindings")
    return()
endif(NOT wisun_sources)

########################################################################
# Check for pygccxml
########################################################################
gr_python_check_module_raw("pygccxml" "import pygccxml" PYGCCXML_FOUND)

include(GrPybind)

########################################################################
# Python Bindings
########################################################################

# keep this list sorted, so that a missing entry is easy to spot
list(APPEND wisun_python_files
    clipping_detector_c_python.cc
    correlate_sync_word_bb_python.cc
    data_whitening_bb_python.cc
    gated_power_squelch_relative_cc_python.cc
    packet_data_gate_bb_python.cc
    pdu_add_pcap_header_python.cc
    pdu_add_pcapng_header_python.cc
    pdu_duplicate_monitor_python.cc
    pdu_fcs_check_python.cc
    pdu_fec_decode_python.cc
    power_squelch_relative_cc_python.cc
    rssi_tag_cc_python.cc
    tag_based_dc_correction_ff_python.cc python_bindings.cc)

gr_pybind_make_oot(wisun ../../.. gr::wisun "${wisun_python_files}")

# copy bindings extension for use in QA test module
add_custom_command(
    TARGET wisun_python
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:wisun_python>
            ${PROJECT_BINARY_DIR}/test_modules/gnuradio/wisun/)

install(
    TARGETS wisun_python
    DESTINATION ${GR_PYTHON_DIR}/gnuradio/wisun
    COMPONENT pythonapi)
