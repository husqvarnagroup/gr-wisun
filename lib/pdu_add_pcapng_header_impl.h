/* -*- c++ -*- */
/*
 * Copyright 2026 GARDENA GmbH.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_IMPL_H
#define INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_IMPL_H

#include <gnuradio/wisun/pdu_add_pcapng_header.h>

namespace gr {
namespace wisun {

/*
 * PCAPNG: Section Header Block (SHB)
 */

#pragma pack(push, 1)
/*
 *                         1                   2                   3
 *     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  0 |                   Block Type = 0x0A0D0D0A                     |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  4 |                      Block Total Length                       |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  8 |                      Byte-Order Magic                         |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 12 |          Major Version        |         Minor Version         |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 16 |                                                               |
 *    |                          Section Length                       |
 *    |                                                               |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 24 /                                                               /
 *    /                      Options (variable)                       /
 *    /                                                               /
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *    |                      Block Total Length                       |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 */
struct pcapng_section_header_block_no_options {
    uint32_t block_type;
    uint32_t block_total_length;
    uint32_t byte_order_magic;
    uint16_t major_version;
    uint16_t minor_version;
    uint64_t section_length;
    uint32_t block_total_length_dup;
};
static_assert(sizeof(struct pcapng_section_header_block_no_options) == 28);
#pragma pack(pop)

/*
 * PCAP: Interface Description Block (IDB) (inital part only)
 */

#pragma pack(push, 1)
/*
 *                         1                   2                   3
 *     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  0 |                    Block Type = 0x00000001                    |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  4 |                      Block Total Length                       |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  8 |           LinkType            |           Reserved            |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 12 |                            SnapLen                            |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 16 /                                                               /
 *    /                      Options (variable)                       /
 *    /                                                               /
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *    |                      Block Total Length                       |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 */
struct pcapng_interface_description_block_base {
    uint32_t block_type;
    uint32_t block_total_length;
    uint16_t link_type;
    uint16_t reserved;
    uint32_t snap_length;
};
static_assert(sizeof(struct pcapng_interface_description_block_base) == 16);
#pragma pack(pop)

/*
 * PCAPNG: Enhanced Packet Block (EPB)  (initial part only)
 */

#pragma pack(push, 1)
/*
 *                         1                   2                   3
 *     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  0 |                    Block Type = 0x00000006                    |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  4 |                      Block Total Length                       |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *  8 |                         Interface ID                          |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 12 |                        Timestamp (High)                       |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 16 |                        Timestamp (Low)                        |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 20 |                    Captured Packet Length                     |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 24 |                    Original Packet Length                     |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * 28 /                                                               /
 *    /                          Packet Data                          /
 *    /              variable length, padded to 32 bits               /
 *    /                                                               /
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *    /                                                               /
 *    /                      Options (variable)                       /
 *    /                                                               /
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 *    |                      Block Total Length                       |
 *    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 */
struct pcapng_enhanced_packet_block_base {
    uint32_t block_type;
    uint32_t block_total_length;
    uint32_t interface_id;
    uint32_t timestamp_high;
    uint32_t timestamp_low;
    uint32_t captured_packet_length;
    uint32_t original_packet_length;
};
static_assert(sizeof(struct pcapng_enhanced_packet_block_base) == 28);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header {
    uint8_t version;
    uint8_t padding;
    uint16_t tap_header_length;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header) == 4);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT TLV types
 */
enum ieee802_15_4_tap_dlt_tlv_types {
    IEEE802_15_4_TAP_DLT_TLV_TYPE_FCS_TYPE                 = 0,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_RSS                      = 1,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_BIT_RATE                 = 2,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_CHANNEL_ASSIGNMENT       = 3,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_SUN_PHY_INFORMATION      = 4,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_START_OF_FRAME_TIMESTAMP = 5,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_END_OF_FRAME_TIMESTAMP   = 6,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_ASN                      = 7,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_START_OF_SLOT_TIMESTAMP  = 8,
    IEEE802_15_4_TAP_DLT_TLV_TYPE_TIMESLOT_LENGTH          = 9,
};

/*
 * IEEE 802.15.4 TAP DLT header: FCS Type
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_fcs_type {
    uint16_t type;
    uint16_t length;
    uint8_t fcs_type;
    uint8_t padding1;
    uint16_t padding2;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_fcs_type) == 8);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: Received Signal Strength (RSS)
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_rss {
    uint16_t type;
    uint16_t length;
    float value;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_rss) == 8);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: Bit Rate
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_bit_rate {
    uint16_t type;
    uint16_t length;
    uint32_t bit_rate;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_bit_rate) == 8);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: Channel Assignment
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_channel_assignment {
    uint16_t type;
    uint16_t length;
    uint16_t channel_number;
    uint8_t channel_page;
    uint8_t padding;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_channel_assignment) == 8);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: SUN PHY Information
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_sun_phy_information {
    uint16_t type;
    uint16_t length;
    uint8_t phy_band;
    uint8_t phy_type;
    uint8_t phy_mode;
    uint8_t padding;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_sun_phy_information) == 8);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: Start of Frame Timestamp
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_start_of_frame_timestamp {
    uint16_t type;
    uint16_t length;
    uint64_t nanoseconds;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_start_of_frame_timestamp) == 12);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: End of Frame Timestamp
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_end_of_frame_timestamp {
    uint16_t type;
    uint16_t length;
    uint64_t nanoseconds;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_end_of_frame_timestamp) == 12);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: Absolute Slot Number (ASN)
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_absolute_slot_number {
    uint16_t type;
    uint16_t length;
    uint64_t asn;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_absolute_slot_number) == 12);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: Start of Slot Timestamp
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_start_of_slot_timestamp {
    uint16_t type;
    uint16_t length;
    uint64_t nanoseconds;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_start_of_slot_timestamp) == 12);
#pragma pack(pop)

/*
 * IEEE 802.15.4 TAP DLT header: Start of Slot Timestamp
 */

#pragma pack(push, 1)
struct ieee802_15_4_tap_dlt_header_timeslot_length {
    uint16_t type;
    uint16_t length;
    uint32_t microseconds;
};
static_assert(sizeof(struct ieee802_15_4_tap_dlt_header_timeslot_length) == 8);
#pragma pack(pop)

class pdu_add_pcapng_header_impl : public pdu_add_pcapng_header
{
private:
    bool d_prepend_section_header_block;
    bool d_section_header_block_done;
    bool d_prepend_interface_description_block;
    bool d_interface_description_block_done;
    bool d_use_tap_dlt;

public:
    pdu_add_pcapng_header_impl(const bool prepend_section_header_block,
                               const bool prepend_interface_description_block,
                               const bool use_tap_dlt);
    ~pdu_add_pcapng_header_impl();

    void handle_msg(pmt::pmt_t msg);
};

} // namespace wisun
} // namespace gr

#endif /* INCLUDED_WISUN_PDU_ADD_PCAPNG_HEADER_IMPL_H */
