// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//
// THIS is DEFINES for pre-compiled header for Engine Project
//

#pragma once

#define WIN32_LEAN_AND_MEAN  // windows.h decrease size
#define _WIN32_WINNT 0x0600  // required by some packets
#define _CRT_SECURE_NO_WARNINGS

#define _SILENCE_CXX17_STRSTREAM_DEPRECATION_WARNING  // strstream in xlog

#define ASIO_STANDALONE                                    // no boost
#define ASIO_HEADER_ONLY                                   // to lazy to add cpp
#define ASIO_NO_DEPRECATED                                 // be nice
#define _SILENCE_CXX17_ALLOCATOR_VOID_DEPRECATION_WARNING  // Microsoft is not
                                                           // smart enough

#define FMT_HEADER_ONLY

#define NOMINMAX  // for Windows

#define _SILENCE_CLANG_COROUTINE_MESSAGE  // clang coroutines
