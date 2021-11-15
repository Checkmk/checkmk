// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "StringUtils.h"

#include <algorithm>
#include <cctype>
#include <iomanip>
#include <sstream>
#include <type_traits>

#include "OStreamStateSaver.h"

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

bool starts_with(std::string_view input, std::string_view test) {
    return input.size() >= test.size() &&
           input.compare(0, test.size(), test) == 0;
}

bool ends_with(std::string_view input, std::string_view test) {
    return input.size() >= test.size() &&
           input.compare(input.size() - test.size(), std::string::npos, test) ==
               0;
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

// Due to legacy reasons, we allow spaces as a separator between the parts of a
// composite key. To be able to use spaces in the parts of the keys themselves,
// we allow a semicolon, too, and look for that first.
std::tuple<std::string, std::string> splitCompositeKey2(
    const std::string &composite_key) {
    auto semicolon = composite_key.find(';');
    return semicolon == std::string::npos
               ? mk::nextField(composite_key)
               : make_tuple(mk::rstrip(composite_key.substr(0, semicolon)),
                            mk::rstrip(composite_key.substr(semicolon + 1)));
}

std::tuple<std::string, std::string, std::string> splitCompositeKey3(
    const std::string &composite_key) {
    const auto &[part1, rest] = splitCompositeKey2(composite_key);
    const auto &[part2, part3] = splitCompositeKey2(rest);
    return {part1, part2, part3};
}

std::string join(const std::vector<std::string> &values,
                 const std::string &separator) {
    std::string result;
    auto it = values.cbegin();
    auto end = values.cend();
    if (it != end) {
        result.append(*it++);
    }
    while (it != end) {
        result.append(separator).append(*it++);
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

std::ostream &operator<<(std::ostream &os, const escape_nonprintable &enp) {
    OStreamStateSaver s{os};
    os << std::hex << std::uppercase << std::setfill('0');
    for (auto ch : enp.buffer) {
        int uch{static_cast<unsigned char>(ch)};
        if (std::isprint(uch) != 0 && ch != '\\') {
            os << ch;
        } else {
            os << "\\x" << std::setw(2) << uch;
        }
    }
    return os;
}

std::pair<std::string, std::string> nextField(const std::string &str,
                                              const std::string &chars) {
    auto s = lstrip(str, chars);
    auto pos = s.find_first_of(chars);
    return pos == std::string::npos
               ? std::make_pair(s, "")
               : std::make_pair(s.substr(0, pos), s.substr(pos + 1));
}

std::string replace_first(const std::string &str, const std::string &from,
                          const std::string &to) {
    if (str.empty() && from.empty()) {
        return "";
    }
    size_t match = str.find(from);
    if (match == std::string::npos) {
        return str;
    }
    std::string result;
    result.reserve(str.size() + to.size() - from.size());
    return result.append(str, 0, match)
        .append(to)
        .append(str, match + from.size());
}

std::string replace_all(const std::string &str, const std::string &from,
                        const std::string &to) {
    std::string result;
    result.reserve(str.size());
    size_t added_after_match = from.empty() ? 1 : 0;
    size_t pos = 0;
    size_t match = 0;
    while ((match = str.find(from, pos)) != std::string::npos) {
        result.append(str, pos, match - pos)
            .append(to)
            .append(str, pos, added_after_match);
        pos = match + from.size() + added_after_match;
    }
    return result.append(str, pos - added_after_match);
}

std::string from_multi_line(const std::string &str) {
    return replace_all(str, "\n", R"(\n)");
}

std::string to_multi_line(const std::string &str) {
    return replace_all(str, R"(\n)", "\n");
}

#ifdef CMC
std::string ipv4ToString(in_addr_t ipv4_address) {
    char addr_buf[INET_ADDRSTRLEN];
    struct in_addr ia = {ipv4_address};
    inet_ntop(AF_INET, &ia, addr_buf, sizeof(addr_buf));
    return addr_buf;
}
#endif
}  // namespace mk
