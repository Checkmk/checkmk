// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// C++ cross platform support for OS and compilers and targets
#pragma once
#if !defined(___TGT_H)
#define ___TGT_H

#if defined(DEBUG) || defined(DBG) || defined(_DEBUG)
#define DEBUG_TARGET 1
#endif

#if defined(_MSC_VER)
#define WINDOWS_OS 1
#define MSC_COMPILER 1
#endif

namespace tgt {
constexpr bool IsDebug() {
#if defined(DEBUG_TARGET)
    return true;
#else
    return false;
#endif
}

constexpr bool Is64bit() {
#if defined(_WIN64)
    return true;
#else
    return false;
#endif
}

constexpr bool IsRelease() { return !IsDebug(); }

constexpr bool IsWindows() {
#if defined(WINDOWS_OS)
    return true;
#else
    return false;
#endif
}

}  // namespace tgt

#endif  // ___TGT_H
