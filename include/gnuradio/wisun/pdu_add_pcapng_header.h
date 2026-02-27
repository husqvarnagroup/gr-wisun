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
 * \brief <+description of block+>
 * \ingroup wisun
 *
 */
class WISUN_API pdu_add_pcapng_header : virtual public gr::block
{
public:
    typedef std::shared_ptr<pdu_add_pcapng_header> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of wisun::pdu_add_pcapng_header.
     *
     * To avoid accidental use of raw pointers, wisun::pdu_add_pcapng_header's
     * constructor is in a private implementation
     * class. wisun::pdu_add_pcapng_header::make is the public interface for
     * creating new instances.
     */
    static sptr make(const bool prepend_section_header_block,
                     const bool prepend_interface_description_block);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_H */
