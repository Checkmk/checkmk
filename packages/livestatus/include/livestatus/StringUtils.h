// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringUtils_h
#define StringUtils_h

#include <netinet/in.h>

#include <bitset>
#include <cstddef>
#include <iterator>
#include <ostream>
#include <string>
#include <string_view>
#include <system_error>
#include <tuple>
#include <utility>
#include <vector>

namespace mk {
std::string unsafe_tolower(const std::string &str);
std::string unsafe_toupper(const std::string &str);

std::string replace_chars(const std::string &str,
                          const std::string &chars_to_replace,
                          char replacement);

std::vector<std::string> split(const std::string &str, char delimiter);

std::tuple<std::string, std::string> splitCompositeKey2(
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

struct escape_nonprintable {
    std::string_view buffer;
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

std::string ipv4ToString(in_addr_t ipv4_address);

namespace ec {
bool is_none(const std::string &str);
std::vector<std::string> split_list(const std::string &str);
}  // namespace ec

bool is_utf8(std::string_view s);

// -----------------------------------------------------------------------------
// We basically use a std::string_view argument like a stream below.

void skip_whitespace(std::string_view &str);

// An argument starts with the first non-whitespace character and extends up to
// the next whitespace character. Optionally, the argument can be in single
// quotes, where 2 consecutive quotes are treated as a verbatim quote.
std::string next_argument(std::string_view &str);

// TODO: Switch to std::from_chars after with llvm 20
std::pair<char *, std::error_code> from_chars(const char *first,
                                              const char * /* last */,
                                              double &value);
}  // namespace mk

template <size_t N>
struct FormattedBitSet {
    std::bitset<N> value;
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
