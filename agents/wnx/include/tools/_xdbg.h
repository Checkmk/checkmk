// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// //////////////////////////////////////////////////////////////////////////
// xdbg
// simplified hardware breakpoints file
// //////////////////////////////////////////////////////////////////////////

// Setup
#pragma once
// Target determination
#if defined(DBG) || defined(_DEBUG) || defined(DEBUG)
#define KDBG_DEBUG
#endif

namespace xdbg {
#if defined(NTDRV)
inline void hardcodedBP() { DbgBreakPoint(); }
#elif defined(NTVIDEO)
inline void hardcodedBP() { EngDebugBreak(); }
#elif defined(WIN32)
inline void hardcodedBP() noexcept { DebugBreak(); }
#elif defined(LINUX)
#if defined(__arm__)
inline void hardcodedBP() { ; }
#else
inline void hardcodedBP() { asm("int $3"); }
#endif
#elif defined(__APPLE__)
inline void hardcodedBP() { ; }
#else
inline void hardcodedBP() { ; }
#endif

#if !defined(KDBG_NO_BP) && defined(KDBG_DEBUG)
inline void bp() noexcept { hardcodedBP(); }
#if !defined(BP)
#define BP xdbg::bp()
#endif

#if !defined(BPO)
#define BPO                     \
    do {                        \
        static int i = 0;       \
        i++;                    \
        if (i == 1) xdbg::bp(); \
    } while (0)
#endif
#else
inline void bp() {}
#if !defined(BP)
#define BP \
    do {   \
    } while (0)
#endif

#if !defined(BPO)
#define BPO \
    do {    \
    } while (0)
#endif
#endif
}  // namespace xdbg
