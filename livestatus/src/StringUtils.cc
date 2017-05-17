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

// https://github.com/include-what-you-use/include-what-you-use/issues/434
// IWYU pragma: no_include <type_traits>
#include "StringUtils.h"
#include <algorithm>
#include <cctype>
#include <sstream>

#ifdef CMC
#include <arpa/inet.h>
#include <sys/socket.h>
#endif

using std::pair;
using std::string;
using std::transform;
using std::vector;

namespace mk {

string unsafe_tolower(const string &str) {
    string result = str;
    transform(str.begin(), str.end(), result.begin(), ::tolower);
    return result;
}

#ifdef CMC
string unsafe_toupper(const string &str) {
    string result = str;
    transform(str.begin(), str.end(), result.begin(), ::toupper);
    return result;
}
#endif

bool starts_with(const string &input, const string &test) {
    return input.size() >= test.size() &&
           std::equal(test.begin(), test.end(), input.begin());
}

vector<string> split(const string &str, char delimiter) {
    std::istringstream iss(str);
    vector<string> result;
    string field;
    while (std::getline(iss, field, delimiter)) {
        result.push_back(field);
    }
    return result;
}

string lstrip(const string &str, const string &chars) {
    auto pos = str.find_first_not_of(chars);
    return pos == string::npos ? "" : str.substr(pos);
}

string rstrip(const string &str, const string &chars) {
    auto pos = str.find_last_not_of(chars);
    return pos == string::npos ? "" : str.substr(0, pos + 1);
}

string strip(const string &str, const string &chars) {
    return rstrip(lstrip(str, chars), chars);
}

pair<string, string> nextField(const string &str, const string &chars) {
    auto s = lstrip(str, chars);
    auto pos = s.find_first_of(chars);
    return pos == string::npos ? make_pair(s, "")
                               : make_pair(s.substr(0, pos), s.substr(pos + 1));
}

#ifdef CMC
string ipv4ToString(in_addr_t ipv4_address) {
    char addr_buf[INET_ADDRSTRLEN];
    struct in_addr ia = {ipv4_address};
    inet_ntop(AF_INET, &ia, addr_buf, sizeof(addr_buf));
    return addr_buf;
}

string portToString(in_port_t port) { return std::to_string(ntohs(port)); }
#endif
}  // namespace mk
