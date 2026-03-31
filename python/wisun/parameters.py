# coding: utf-8
#
# Copyright (c) 2026 Gardena GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# References:
# [802.15.4] IEEE 802.15.4-2020
# [Wi-SUN PHY] Wi-SUN Alliance PHY Technical Profile Specification Rev. 2.03

"""Wi-SUN parameters as specified in 802.15.4-2020."""

#
# IEEE 802.15.4-2020
#

# [802.15.4] Table 7-21: Frequency band identifier values
FREQUENCY_BAND_IDENTIFIERS = {
    # Frequency band identifier: Band designation
    0: "169 MHz",
    1: "450 MHz",
    2: "470 MHz",
    3: "780 MHz",
    4: "863 MHz",
    5: "896 MHz",
    6: "901 MHz",
    7: "915 MHz",
    8: "917 MHz",
    9: "920 MHz",
    10: "928 MHz",
    11: "920 MHz",
    12: "1427 MHz",
    13: "2450 MHz",
    14: "866 MHz",
    15: "870 MHz",
    # Table 7-22: Frequency band identifier values - extended
    16: "915 MHz-a",
    17: "915 MHz-b",
    18: "915 MHz-c",
    19: "915 MHz-d",
    20: "915 MHz-e",
    21: "919 MHZ",
    22: "920 MHz-a",
    23: "920 MHz-b",
    24: "867 MHz",
    # 25–31: Reserved
}

# IEEE 802.15.4-2020 Table 7-23: Modulation scheme encoding
PHY_TYPES = {
    # PHY type: Modulation scheme
    0: "FSK-A",
    1: "FSK-B",
    2: "O-QPSK-A",
    3: "O-QPSK-B",
    4: "O-QPSK-C",
    5: "OFDM Option 1",
    6: "OFDM Option 2",
    7: "OFDM Option 3",
    8: "OFDM Option 4",
    9: "FSK-C",
    # 10–15: Reserved
}

PHY_MODES = {
    # FSK-A
    0: {  # IEEE 802.15.4-2020 Table 7-24: FSK-A PHY mode encoding
        # PHY Mode ID: FSK PHY mode (data rate [b/s], modulation, modulation index, channel spacing [Hz])
        0:  (4_800, "2-FSK", 1.0,  12_500),
        1:  (9_600, "4-FSK", 0.33, 12_500),
        2: (10_000, "2-FSK", 0.5,  12_500),
        3: (20_000, "2-FSK", 0.5,  12_500),
        4: (40_000, "2-FSK", 0.5,  12_500),
        5:  (4_800, "2-FSK", 0.5,  12_500),
        6:  (2_400, "2-FSK", 2.0,  12_500),
        7:  (9_600, "4-FSK", 0.33, 12_500),


    },

    # FSK-B
    1: {  # IEEE 802.15.4-2020 Table 7-25: FSK-B PHY mode encoding
        # PHY Mode ID: FSK PHY mode (data rate [b/s], modulation, modulation index, channel spacing [Hz])
        0:   (50_000, "2-FSK", 1.0,  200_000),
        1:  (100_000, "2-FSK", 1.0,  400_000),
        2:  (150_000, "2-FSK", 0.5,  400_000),
        3:  (200_000, "2-FSK", 0.5,  400_000),
        4:  (200_000, "4-FSK", 0.33, 400_000),
        5:  (200_000, "2-FSK", 1.0,  600_000),
        6:  (400_000, "4-FSK", 0.33, 600_000),
        7:  (100_000, "2-FSK", 0.5,  200_000),
        8:   (50_000, "2-FSK", 0.5,  100_000),
        9:  (150_000, "2-FSK", 0.5,  200_000),
        10: (300_000, "2-FSK", 0.5,  400_000),
    },

    # 2-4: O-QPSK: not supported yet

    # 5-8: OFDM: not supported yet

    # FSK-C
    9: {  # IEEE 802.15.4-2020 Table 7-26: FSK-C PHY mode encoding
        # PHY Mode ID: FSK PHY mode (data rate [b/s], modulation, modulation index, channel spacing [Hz])
        0: (10_000, "2-FSK", 1.0,  50_000),
        1: (20_000, "2-FSK", 1.0, 100_000),
    },
}

#
# Wi-SUN PHY Technical Profile Specification Rev2.03
#

# Wi-SUN Country Codes
# [Wi-SUN PHY] 3.2 Country Codes
WISUN_COUNTRY_CODES = {
    'AU/NZ': "Australia & New Zealand",
    'BZ': "Brazil",
    'CN': "China",
    'EU': "Europe",
    'HK': "Hong Kong",
    'IN': "India",
    'JP': "Japan",
    'KR': "Korea",
    'MX': "Mexico",
    'MY': "Malaysia",
    'NA': "North America (U.S. & Canada)",
    'PH': "Philippines",
    'SG': "Singapore",
    'TH': "Thailand",
    'VN': "Vietnam",
    'WW': "Worldwide"
}

# Wi-SUN PHY Types
# [Wi-SUN] 5.2 PHY Operating Mode (Table 3)
WISUN_PHY_TYPES = {
    0: "FSK without FEC",
    1: "FSK with NRNSC FEC",
    2: "OFDM Option1",
    3: "OFDM Option2",
    4: "OFDM Option3",
    5: "OFDM Option4",
}

# Wi-SUN PHY Modes
# [Wi-SUN] 5.2 PHY Operating Mode (Table 4: FSK PhyMode Field Enumeration)
WISUN_PHY_MODES_FSK = {
    # Modulation Level, Symbol Rate, Modulation Index, Legacy PHY Operating Mode
    1: ("2-FSK",  50_000, 0.5, "#1a"),
    2: ("2-FSK",  50_000, 1.0, "#1b"),
    3: ("2-FSK", 100_000, 0.5, "#2a"),
    4: ("2-FSK", 100_000, 1.0, "#2b"),
    5: ("2-FSK", 150_000, 0.5, "#3"),
    6: ("2-FSK", 200_000, 0.5, "#4a"),
    7: ("2-FSK", 200_000, 1.0, "#4b"),
    8: ("2-FSK", 300_000, 0.5, "#5"),
}

# [Wi-SUN] 5.2 PHY Operating Mode (Table 5: OFDM PhyMode Enumeration)
WISUN_PHY_MODES_OFDM = {
    0: "MCS0",
    1: "MCS1",
    2: "MCS2",
    3: "MCS3",
    4: "MCS4",
    5: "MCS5",
    6: "MCS6",
}

# Wi-SUN Channel Plans
# [Wi-SUN] 5.3 Regulatory Channel Plan (Table 7: Regulatory Channel Plans)
WISUN_CHANNEL_PLANS = {
    # Channel Plan ID: (Channel Plan Name, Channel Spacing [Hz], Channel 0 Center Frequency [Hz])
    1:     ("902_928_200", 0.2e6,   902.2e6),
    2:     ("902_928_400", 0.4e6,   902.4e6),
    3:     ("902_928_600", 0.6e6,   902.6e6),
    4:     ("902_928_800", 0.8e6,   902.8e6),
    5:    ("902_928_1200", 1.2e6,   903.2e6),
    21:    ("920_928_200", 0.2e6,   920.6e6),
    22:    ("920_928_400", 0.4e6,   920.9e6),
    23:    ("920_928_600", 0.6e6,   920.8e6),
    24:    ("920_928_800", 0.8e6,   921.1e6),
    32:    ("863_870_100", 0.1e6,   863.1e6),
    33:    ("863_870_200", 0.2e6,   863.1e6),
    34:    ("870_876_100", 0.1e6,   870.1e6),
    35:    ("870_876_200", 0.2e6,   870.2e6),
    36:    ("863_876_100", 0.1e6,   863.1e6),
    37:    ("863_876_200", 0.2e6,   863.1e6),
    39:    ("865_868_100", 0.1e6,   865.1e6),
    40:    ("865_868_200", 0.2e6,   865.1e6),
    41:    ("866_869_100", 0.1e6,   866.1e6),
    42:    ("866_869_200", 0.2e6,   866.1e6),
    43:    ("866_869_400", 0.4e6,   866.3e6),
    48:    ("915_928_200", 0.2e6,   915.2e6),
    49:    ("915_928_400", 0.4e6,   915.4e6),
    64:    ("920_925_200", 0.2e6,   920.2e6),
    65:    ("920_925_400", 0.4e6,   920.4e6),
    80:    ("919_923_200", 0.2e6,   919.2e6),
    81:    ("919_923_400", 0.4e6,   919.2e6),
    96:    ("917_923_200", 0.2e6,   917.1e6),
    97:    ("917_923_400", 0.4e6,   917.3e6),
    112: ("2400_2483_200", 0.2e6,  2400.2e6),
    113: ("2400_2483_400", 0.4e6,  2400.4e6),
    128:   ("920_925_250", 0.25e6,  920.625e6),
    144:   ("779_787_200", 0.2e6,   779.2e6),
    145:   ("779_787_400", 0.4e6,   779.4e6),
    160:   ("470_510_200", 0.2e6,   470.2e6),
}


# Wi-SUN: Supported Frequency Bands and Channel Parameters
# [Wi-SUN] 5.4 Frequency Bands and Channel Parameters (Table 8)
WISUN_FREQUENCY_BANDS = {  # informal only
    # Channel Plan ID: Frequency Band [MHz]
    1:   (902, 928),
    2:   (902, 928),
    3:   (902, 928),
    4:   (902, 928),
    5:   (902, 928),
    21:  (920, 928),
    22:  (920, 928),
    23:  (920, 928),
    24:  (920, 928),
    32:  (863, 870),
    33:  (863, 870),
    34:  (870, 876),
    35:  (870, 876),
    36:  (863, 876),
    37:  (863, 876),
    39:  (865, 868),
    40:  (865, 868),
    41:  (866, 869),
    42:  (866, 869),
    43:  (866, 869),
    48:  (915, 928),  # in PH only 915 - 918
    49:  (915, 928),  # in PH only 915 - 918
    64:  (920, 925),
    65:  (920, 925),
    80:  (919, 923),
    81:  (919, 923),
    96:  (917, 923.5),
    97:  (917, 923.5),
    112: (2400, 2483.5),
    113: (2400, 2483.5),
    128: (920.5, 924.5),
    160: (470, 510),
}

# [Wi-SUN] 5.4 Frequency Bands and Channel Parameters (Table 8)
WISUN_SUPPORTED_PARAMETERS = {
    # (Regulatory Domain, Channel Plan ID): (Valid Total Number of Channels, Supported PHY Mode IDs, Channel Mask)
    ("EU", 32): (
        62,
        {0x01, 0x11},
        "00:00:00:00:00:00:80:e1:e6"
    ),
    ("EU", 33): (
        29,
        {0x03, 0x05, 0x13, 0x15, 0x54, 0x55, 0x56},
        "00:00:00:d8:fb"
    ),
    ("EU", 34): (
        55,
        {0x01, 0x11},
        "00:00:00:00:00:00:80"
    ),
    ("EU", 35): (
        27,
        {0x03, 0x05, 0x13, 0x15, 0x54, 0x55, 0x56},
        "00:00:00:f8"
    ),
    ("EU", 36): (
        118,
        {0x01, 0x11},
        "00:00:00:00:00:00:80:e1:06:00:00:00:00:00:00:e0"
    ),
    ("EU", 37): (
        56,
        {0x03, 0x05, 0x13, 0x15, 0x54, 0x55, 0x56},
        "00:00:00:D8:03:00:00:C0"
    ),
    ("NA", 1): (
        129,
        {0x02, 0x03, 0x12, 0x13, 0x54, 0x55, 0x56},
        "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:fe"
    ),
    ("NA", 2): (
        64,
        {0x05, 0x06, 0x15, 0x16, 0x44, 0x45, 0x46},
        "00:00:00:00:00:00:00:00"
    ),
    ("NA", 3): (
        42,
        {0x08, 0x18},
        "00:00:00:00:00:fc"
    ),
    ("NA", 4): (
        31,
        {0x33, 0x34, 0x35, 0x36},
        "00:00:00:80"
    ),
    ("NA", 5): (
        20,
        {0x22, 0x23, 0x24, 0x25, 0x26},
        "00:00:f0"
    ),
    ("BZ", 1): (
        78,
        {0x02, 0x03, 0x12, 0x13, 0x54, 0x55, 0x56},
        "00:c0:ff:ff:ff:ff:ff:ff:01:00:00:00:00:00:00:00:fe"
    ),
    ("BZ", 2): (
        37,
        {0x05, 0x06, 0x15, 0x16, 0x44, 0x45, 0x46},
        "c0:ff:ff:ff:01:00:00:00"
    ),
    ("BZ", 3): (
        24,
        {0x08, 0x18},
        "f0:ff:3f:00:00:fc"
    ),
    ("BZ", 4): (
        16,
        {0x33, 0x34, 0x35, 0x36},
        "fc:ff:01:80"
    ),
    ("BZ", 5): (
        10,
        {0x22, 0x23, 0x24, 0x25, 0x26},
        "fe:07:f0"
    ),
    ("JP", 21): (
        29,
        {0x02, 0x12, 0x54, 0x55, 0x56},
        "ff:01:00:00:c0"
    ),
    ("JP", 22): (
        14,
        {0x04, 0x05, 0x14, 0x15, 0x44, 0x45, 0x46},
        "0f:00:fc"
    ),
    ("JP", 23): (
        9,
        {0x07, 0x08, 0x17, 0x18},
        "07:f0"
    ),
    ("JP", 24): (
        7,
        {0x33, 0x34, 0x35, 0x36},
        "03:fe"
    ),
    ("CN", 160): (
        199,
        {0x02, 0x03, 0x05, 0x12, 0x13, 0x15},
        "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:80"
    ),
    ("CN", 128): (
        16,
        {0x02, 0x03, 0x05, 0x12, 0x13, 0x15},
        "00:00"
    ),
    ("IN", 39): (
        29,
        {0x01, 0x11},
        "00:00:00:e0"
    ),
    ("IN", 40): (
        15,
        {0x03, 0x05, 0x13, 0x15, 0x54, 0x55, 0x56},
        "00:80"
    ),
    ("SG", 41): (
        29,
        {0x01, 0x11},
        "00:00:00:e0"
    ),
    ("SG", 42): (
        15,
        {0x03, 0x05, 0x13, 0x15, 0x54, 0x55, 0x56},
        "00:80"
    ),
    ("SG", 43): (
        7,
        {0x06, 0x08, 0x16, 0x18},
        "80"
    ),
    ("SG", 64): (
        24,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:00"
    ),
    ("SG", 65): (
        12,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:f0"
    ),
    ("MX", 1): (
        129,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:fe"
    ),
    ("MX", 2): (
        64,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:00:00:00:00:00:00:00"
    ),
    ("AU/NZ", 48): (
        64,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:00:00:00:00:00:00"
    ),
    ("AU/NZ", 49): (
        32,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:00:00:00"
    ),
    ("KR", 96): (
        32,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:00:00"
    ),
    ("KR", 97): (
        16,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:00"
    ),
    ("PH", 48): (
        14,
        {0x02, 0x03, 0x12, 0x13},
        "00:c0:ff:ff:ff:ff:ff:ff"
    ),
    ("PH", 49): (
        7,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "80:ff:ff:ff"
    ),
    ("MY", 80): (
        19,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:f8"
    ),
    ("MY", 81): (
        10,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:fc"
    ),
    ("HK", 64): (
        24,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:00"
    ),
    ("HK", 65): (
        12,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:f0"
    ),
    ("TH", 64): (
        24,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:00"
    ),
    ("TH", 65): (
        12,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:f0"
    ),
    ("VN", 64): (
        24,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:00"
    ),
    ("VN", 65): (
        12,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:f0"
    ),
    ("WW", 112): (
        416,
        {0x02, 0x03, 0x12, 0x13},
        "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:"
        "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00"
    ),
    ("WW", 113): (
        207,
        {0x05, 0x06, 0x08, 0x15, 0x16, 0x18},
        "00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:80"
    ),
}
