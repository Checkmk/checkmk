// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Assorted routines
#pragma once
#include <wtypes.h>

#include <cstdint>
namespace wtools {

/// Replacement for INVALID_HANDLE_VALUE
inline HANDLE InvalidHandle() noexcept {
    // conversion to satisfy Win32 API and C++:
    return reinterpret_cast<HANDLE>(
        static_cast<size_t>(static_cast<LONG_PTR>(-1)));
}

inline bool IsInvalidHandle(HANDLE h) noexcept {
    //
    return InvalidHandle() == h;
}

inline bool IsGoodHandle(HANDLE h) noexcept {
    return h != nullptr && h != InvalidHandle();
}

inline bool IsBadHandle(HANDLE h) noexcept { return !IsGoodHandle(h); }

}  // namespace wtools
