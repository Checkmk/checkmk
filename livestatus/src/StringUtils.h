// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringUtils_h
#define StringUtils_h

#include "config.h"  // IWYU pragma: keep

#include <bitset>
#include <cstddef>
#include <ostream>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

#ifdef CMC
#include <netinet/in.h>
#endif

namespace mk {
std::string unsafe_tolower(const std::string &str);
#ifdef CMC
std::string unsafe_toupper(const std::string &str);
#endif

bool starts_with(std::string_view input, std::string_view test);
bool ends_with(std::string_view input, std::string_view test);

std::vector<std::string> split(const std::string &str, char delimiter);

std::tuple<std::string, std::string> splitCompositeKey2(
    const std::string &composite_key);

std::tuple<std::string, std::string, std::string> splitCompositeKey3(
    const std::string &composite_key);

std::string join(const std::vector<std::string> &values,
                 const std::string &separator);

constexpr auto whitespace = " \t\n\v\f\r";

std::string lstrip(const std::string &str, const std::string &chars);

inline std::string lstrip(const std::string &str) {
    return lstrip(str, whitespace);
}

std::string rstrip(const std::string &str, const std::string &chars);

inline std::string rstrip(const std::string &str) {
    return rstrip(str, whitespace);
}

std::string strip(const std::string &str, const std::string &chars);

inline std::string strip(const std::string &str) {
    return strip(str, whitespace);
}

struct escape_nonprintable {
    const std::string_view buffer;
};

std::ostream &operator<<(std::ostream &os, const escape_nonprintable &enp);

std::pair<std::string, std::string> nextField(const std::string &str,
                                              const std::string &chars);

inline std::pair<std::string, std::string> nextField(const std::string &str) {
    return nextField(str, whitespace);
}

std::string replace_first(const std::string &str, const std::string &from,
                          const std::string &to);

std::string replace_all(const std::string &str, const std::string &from,
                        const std::string &to);

std::string from_multi_line(const std::string &str);
std::string to_multi_line(const std::string &str);

#ifdef CMC
std::string ipv4ToString(in_addr_t ipv4_address);
#endif
}  // namespace mk

template <size_t N>
struct FormattedBitSet {
    const std::bitset<N> &value;
};

template <size_t N>
std::ostream &operator<<(std::ostream &os, const FormattedBitSet<N> &bs) {
    size_t elems = 0;
    os << "{";
    for (size_t pos = 0; pos < N; ++pos) {
        if (bs.value[pos]) {
            os << (elems++ == 0 ? "" : ", ") << pos;
        }
    }
    return os << "}";
}

#endif  // StringUtils_h
