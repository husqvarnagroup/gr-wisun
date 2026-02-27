/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_H
#define INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_H

#include <gnuradio/block.h>
#include <gnuradio/wisun/api.h>

namespace gr {
namespace wisun {

/*!
 * \brief This block adds a PCAP-NG header to each received PDU.
 * \ingroup wisun
 *
 */
class WISUN_API pdu_add_pcapng_header : virtual public gr::block
{
public:
    typedef std::shared_ptr<pdu_add_pcapng_header> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::pdu_add_pcapng_header.
     * \param prepend_section_header_block Whether to add initial PDU with SHB
     * \param prepend_interface_description_block Whether to add initial PDU with IDB
     * \param use_tap_dlt Whether to use IEEE 802.15.4 TAP data link-type instead of
     * regular IEEE 802.15.4 data link-type. This allows adding additional metadata (such
     * as RSSI) to the packets.
     *
     * To avoid accidental use of raw pointers, wisun::pdu_add_pcapng_header's
     * constructor is in a private implementation
     * class. wisun::pdu_add_pcapng_header::make is the public interface for
     * creating new instances.
     */
    static sptr make(const bool prepend_section_header_block,
                     const bool prepend_interface_description_block,
                     const bool use_tap_dlt);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_H */
