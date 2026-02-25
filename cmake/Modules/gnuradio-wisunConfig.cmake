# SPDX-FileCopyrightText: 2026 GNU Radio contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_WISUN gnuradio-wisun)

FIND_PATH(
    GR_WISUN_INCLUDE_DIRS
    NAMES gnuradio/wisun/api.h
    HINTS $ENV{WISUN_DIR}/include
        ${PC_WISUN_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_WISUN_LIBRARIES
    NAMES gnuradio-wisun
    HINTS $ENV{WISUN_DIR}/lib
        ${PC_WISUN_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-wisunTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_WISUN DEFAULT_MSG GR_WISUN_LIBRARIES GR_WISUN_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_WISUN_LIBRARIES GR_WISUN_INCLUDE_DIRS)
