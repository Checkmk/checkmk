// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

#ifndef StringUtils_h
#define StringUtils_h

#include "config.h"  // IWYU pragma: keep
#include <bitset>
#include <cstddef>
#include <ostream>
#include <string>
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

bool starts_with(const std::string &input, const std::string &test);

std::vector<std::string> split(const std::string &str, char delimiter);

std::string lstrip(const std::string &str,
                   const std::string &chars = " \t\n\v\f\r");

std::string rstrip(const std::string &str,
                   const std::string &chars = " \t\n\v\f\r");

std::string strip(const std::string &str,
                  const std::string &chars = " \t\n\v\f\r");

std::pair<std::string, std::string> nextField(
    const std::string &str, const std::string &chars = " \t\n\v\f\r");

#ifdef CMC
std::string ipv4ToString(in_addr_t ipv4_address);
std::string portToString(in_port_t port);
#endif
}  // namespace mk

template <size_t N>
struct FormattedBitSet {
    const std::bitset<N> &value;
};

template <size_t N>
std::ostream &operator<<(std::ostream &os, const FormattedBitSet<N> &bs) {
    size_t elems = 0;
    for (size_t pos = 0; pos < N; ++pos) {
        if (bs.value[pos]) {
            os << (elems++ == 0 ? "{" : ", ") << pos;
        }
    }
    return os << "}";
}

#endif  // StringUtils_h
