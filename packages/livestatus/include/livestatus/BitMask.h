// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BitMask_h
#define BitMask_h

#include <type_traits>

// NOLINTBEGIN(modernize-use-constraints)
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
// NOLINTNEXTLINE(cppcoreguidelines-macro-usage)
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
}  // namespace mk

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
constexpr Enum operator&(Enum x, Enum y) {
    return x &= y;
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
constexpr Enum operator|(Enum x, Enum y) {
    return x |= y;
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
constexpr Enum operator^(Enum x, Enum y) {
    return x ^= y;
}

template <typename Enum, typename = std::enable_if_t<mk::is_bit_mask_v<Enum>>>
constexpr Enum operator~(Enum x) {
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
// NOLINTEND(modernize-use-constraints)

#endif  // BitMask_h
