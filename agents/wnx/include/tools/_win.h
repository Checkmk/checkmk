// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Assorted routines
#pragma once
#include <wtypes.h>

#include <cstdint>
namespace wtools {

constexpr HANDLE InvalidHandle() {
    // conversion to satisfy Win32 API and C++:
    return reinterpret_cast<HANDLE>(
        static_cast<size_t>(static_cast<LONG_PTR>(-1)));
}

inline bool IsInvalidHandle(HANDLE h) {
    //
    return InvalidHandle() == h;
}

inline bool IsGoodHandle(HANDLE h) noexcept {
    return h != nullptr && h != InvalidHandle();
}

inline bool IsBadHandle(HANDLE h) noexcept { return !IsGoodHandle(h); }

}  // namespace wtools
