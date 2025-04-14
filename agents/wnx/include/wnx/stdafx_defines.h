// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

//
// THIS is DEFINES for pre-compiled header for Engine Project
//

#pragma once

#define WIN32_LEAN_AND_MEAN  // windows.h decrease size

#define NOVIRTUALKEYCODES  // VK_*
#define NOWINSTYLES        // WS_*, CS_*, ES_*, LBS_*, SBS_*, CBS_*
#define NOSYSMETRICS       // SM_*
#define NOMENUS            // MF_*
#define NOICONS            // IDI_*
#define NOKEYSTATES        // MK_*
#define NOSYSCOMMANDS      // SC_*
#define NORASTEROPS        // Binary and Tertiary raster ops
#define OEMRESOURCE        // OEM Resource values
#define NOATOM             // Atom Manager routines
#define NOCLIPBOARD        // Clipboard routines
#define NOCOLOR            // Screen colors
#define NODRAWTEXT         // DrawText() and DT_*
#define NOKERNEL           // All KERNEL defines and routines
#define NOMB               // MB_* and MessageBox()
#define NOMEMMGR           // GMEM_*, LMEM_*, GHND, LHND, associated routines
#define NOMETAFILE         // typedef METAFILEPICT
#define NOMINMAX           // Macros min(a,b) and max(a,b)
#define NOSCROLL           // SB_* and scrolling routines
#define NOSOUND            // Sound driver routines
#define NOTEXTMETRIC       // typedef TEXTMETRIC and associated routines
#define NOWH               // SetWindowsHook and WH_*
#define NOWINOFFSETS       // GWL_*, GCL_*, associated routines
#define NOKANJI            // Kanji support stuff.
#define NOHELP             // Help engine interface.
#define NOPROFILER         // Profiler interface.
#define NODEFERWINDOWPOS   // DeferWindowPos routines
#define NOMCX              // Modem Configuration Extensions

#define _WIN32_WINNT 0x0600  // NOLINT

#define _CRT_SECURE_NO_WARNINGS ﻿1  // NOLINT

#define _SILENCE_CXX17_STRSTREAM_DEPRECATION_WARNING   // strstream in xlog
#define _SILENCE_STDEXT_ARR_ITERS_DEPRECATION_WARNING  // std format 9.0

#define ASIO_STANDALONE                                    // no boost
#define ASIO_HEADER_ONLY                                   // to lazy to add cpp
#define ASIO_NO_DEPRECATED                                 // be nice
#define _SILENCE_CXX17_ALLOCATOR_VOID_DEPRECATION_WARNING  // Microsoft is not
                                                           // smart enough

#define FMT_HEADER_ONLY

#define NOMINMAX  // for Windows

#define _SILENCE_CLANG_COROUTINE_MESSAGE  // clang coroutines
#define _SILENCE_STDEXT_ARR_ITERS_DEPRECATION_WARNING
