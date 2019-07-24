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

#include "StringUtils.h"
#include <algorithm>
#include <boost/algorithm/string/replace.hpp>
#include <cctype>
#include <sstream>
#include <type_traits>

#ifdef CMC
#include <arpa/inet.h>
#include <sys/socket.h>
#endif

namespace mk {
std::string unsafe_tolower(const std::string &str) {
    std::string result = str;
    std::transform(str.begin(), str.end(), result.begin(), ::tolower);
    return result;
}

#ifdef CMC
std::string unsafe_toupper(const std::string &str) {
    std::string result = str;
    std::transform(str.begin(), str.end(), result.begin(), ::toupper);
    return result;
}
#endif

bool starts_with(const std::string &input, const std::string &test) {
    return input.size() >= test.size() &&
           std::equal(test.begin(), test.end(), input.begin());
}

std::vector<std::string> split(const std::string &str, char delimiter) {
    std::istringstream iss(str);
    std::vector<std::string> result;
    std::string field;
    while (std::getline(iss, field, delimiter)) {
        result.push_back(field);
    }
    return result;
}

std::string lstrip(const std::string &str, const std::string &chars) {
    auto pos = str.find_first_not_of(chars);
    return pos == std::string::npos ? "" : str.substr(pos);
}

std::string rstrip(const std::string &str, const std::string &chars) {
    auto pos = str.find_last_not_of(chars);
    return pos == std::string::npos ? "" : str.substr(0, pos + 1);
}

std::string strip(const std::string &str, const std::string &chars) {
    return rstrip(lstrip(str, chars), chars);
}

std::pair<std::string, std::string> nextField(const std::string &str,
                                              const std::string &chars) {
    auto s = lstrip(str, chars);
    auto pos = s.find_first_of(chars);
    return pos == std::string::npos
               ? std::make_pair(s, "")
               : std::make_pair(s.substr(0, pos), s.substr(pos + 1));
}

std::string from_multi_line(const std::string &str) {
    return boost::replace_all_copy(str, "\n", R"(\n)");
}

std::string to_multi_line(const std::string &str) {
    return boost::replace_all_copy(str, R"(\n)", "\n");
}

#ifdef CMC
std::string ipv4ToString(in_addr_t ipv4_address) {
    char addr_buf[INET_ADDRSTRLEN];
    struct in_addr ia = {ipv4_address};
    inet_ntop(AF_INET, &ia, addr_buf, sizeof(addr_buf));
    return addr_buf;
}

std::string portToString(in_port_t port) {
    // NOLINTNEXTLINE(readability-isolate-declaration)
    return std::to_string(ntohs(port));
}
#endif
}  // namespace mk
