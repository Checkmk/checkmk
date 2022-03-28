// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Windows Agent Version Data

#pragma once
#if !defined(version_h__)
#define version_h__

#include "wnx_version.h"
#define CHECK_MK_VERSION CMK_WIN_AGENT_VERSION

#define STRINGIZE2(s) #s
#define STRINGIZE(s) STRINGIZE2(s)

// This FILE version, normally no changes
#define VERSION_MAJOR 2
#define VERSION_MINOR 1
#define VERSION_REVISION 0
#define VERSION_BUILD 0

#define VER_FILE_VERSION \
    VERSION_MAJOR, VERSION_MINOR, VERSION_REVISION, VERSION_BUILD
#define VER_FILE_VERSION_STR \
    STRINGIZE(VERSION_MAJOR) \
    "." STRINGIZE(VERSION_MINOR) "." STRINGIZE( \
        VERSION_REVISION) "." STRINGIZE(VERSION_BUILD)

#define VER_PRODUCT_VERSION_STR CMK_WIN_AGENT_VERSION

#ifdef _DEBUG
#define VER_VER_DEBUG VS_FF_DEBUG
#else
#define VER_VER_DEBUG 0
#endif

#define VER_FILEOS VOS_NT_WINDOWS32
#define VER_FILEFLAGS VER_VER_DEBUG
#define VER_FILETYPE VFT_APP

#endif  // version_h__
