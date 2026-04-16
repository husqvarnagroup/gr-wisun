/*
 * Copyright 2020 Free Software Foundation, Inc.
 *
 * This file is part of GNU Radio
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 */

#include <pybind11/pybind11.h>

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <numpy/arrayobject.h>

namespace py = pybind11;

// Headers for binding functions
/**************************************/
// The following comment block is used for
// gr_modtool to insert function prototypes
// Please do not delete
/**************************************/
// BINDING_FUNCTION_PROTOTYPES(
    void bind_correlate_sync_word_bb(py::module& m);
    void bind_packet_data_gate_bb(py::module& m);
    void bind_data_whitening_bb(py::module& m);
    void bind_pdu_add_pcap_header(py::module& m);
    void bind_rssi_tag_cc(py::module& m);
    void bind_power_squelch_relative_cc(py::module& m);
    void bind_tag_based_dc_correction_ff(py::module& m);
    void bind_pdu_add_pcapng_header(py::module& m);
    void bind_gated_power_squelch_relative_cc(py::module& m);
// ) END BINDING_FUNCTION_PROTOTYPES


// We need this hack because import_array() returns NULL
// for newer Python versions.
// This function is also necessary because it ensures access to the C API
// and removes a warning.
void* init_numpy()
{
    import_array();
    return NULL;
}

PYBIND11_MODULE(wisun_python, m)
{
    // Initialize the numpy C API
    // (otherwise we will see segmentation faults)
    init_numpy();

    // Allow access to base block methods
    py::module::import("gnuradio.gr");

    /**************************************/
    // The following comment block is used for
    // gr_modtool to insert binding function calls
    // Please do not delete
    /**************************************/
    // BINDING_FUNCTION_CALLS(
    bind_correlate_sync_word_bb(m);
    bind_packet_data_gate_bb(m);
    bind_data_whitening_bb(m);
    bind_pdu_add_pcap_header(m);
    bind_rssi_tag_cc(m);
    bind_power_squelch_relative_cc(m);
    bind_tag_based_dc_correction_ff(m);
    bind_pdu_add_pcapng_header(m);
    bind_gated_power_squelch_relative_cc(m);
    // ) END BINDING_FUNCTION_CALLS
}