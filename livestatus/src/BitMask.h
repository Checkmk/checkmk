// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef BitMask_h
#define BitMask_h

#include "config.h"  // IWYU pragma: keep
#include <type_traits>

namespace mk {
// Return the enumerator's value as a compile-time constant, see Scott Meyer's
// "Effective Modern C++", item 10.
template <typename Enum>
constexpr auto toUType(Enum e) noexcept {
    return static_cast<std::underlying_type_t<Enum>>(e);
}

// A marker trait which enables the bit mask operators
template <typename Enum>
struct is_bit_mask {
    static const bool value = false;
};

// A helper macro to make the use sites of the marker trait less verbose
#define IS_BIT_MASK(ENUM)               \
    namespace mk {                      \
    template <>                         \
    struct is_bit_mask<ENUM> {          \
        static const bool value = true; \
    };                                  \
    }

// A helper template to make template definitions a bit shorter
template <typename T>
constexpr bool is_bit_mask_v = is_bit_mask<T>::value;
}  // namespace

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
inline constexpr Enum operator&(Enum x, Enum y) {
    return x &= y;
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
inline constexpr Enum operator|(Enum x, Enum y) {
    return x |= y;
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
inline constexpr Enum operator^(Enum x, Enum y) {
    return x ^= y;
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
inline constexpr Enum operator~(Enum x) {
    return Enum(~mk::toUType(x));
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
inline Enum &operator|=(Enum &x, Enum y) {
    return x = Enum(mk::toUType(x) | mk::toUType(y));
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
inline const Enum &operator&=(Enum &x, Enum y) {
    return x = Enum(mk::toUType(x) & mk::toUType(y));
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
inline Enum &operator^=(Enum &x, Enum y) {
    return x = Enum(mk::toUType(x) ^ mk::toUType(y));
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
inline bool is_empty_bit_mask(Enum x) {
    return x == Enum(0);
}

#endif  // BitMask_h
