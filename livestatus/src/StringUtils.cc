// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
bool is_utf8(std::string_view s) {
    // https://www.unicode.org/versions/Unicode15.0.0/ch03.pdf p.125
    // Correct UTF-8 encoding
    // ----------------------------------------------------------------
    // Code Points         First Byte Second Byte Third Byte Fourth Byte
    // U+0000 -   U+007F     00 - 7F
    // U+0080 -   U+07FF     C2 - DF    80 - BF
    // U+0800 -   U+0FFF     E0         A0 - BF     80 - BF
    // U+1000 -   U+CFFF     E1 - EC    80 - BF     80 - BF
    // U+D000 -   U+D7FF     ED         80 - 9F     80 - BF
    // U+E000 -   U+FFFF     EE - EF    80 - BF     80 - BF
    // U+10000 -  U+3FFFF    F0         90 - BF     80 - BF    80 - BF
    // U+40000 -  U+FFFFF    F1 - F3    80 - BF     80 - BF    80 - BF
    // U+100000 - U+10FFFF   F4         80 - 8F     80 - BF    80 - BF
    const auto *end = s.cend();
    for (const char *p = s.cbegin(); p != end; ++p) {
        const unsigned char ch0 = *p;
        if (ch0 < 0x80) {
            continue;
        }
        if (ch0 < 0xC2 || ch0 > 0xF4) {
            // Invalid first byte: 0x80..0xC2 and 0xF5..0xFF
            return false;
        }
        if (ch0 < 0xE0) {
            // 2 byte encoding: C2..DF
            if (end <= &p[1]) {
                return false;
            }
            const unsigned char ch1 = *++p;
            if (ch1 < 0x80 || ch1 > 0xBF) {
                return false;
            }
            continue;
        }
        if (ch0 < 0xF0) {
            // 3 byte encoding: 0xE0..0xEF
            if (end <= &p[2]) {
                return false;
            }
            const unsigned char ch1 = *++p;
            const unsigned char low = ch0 == 0xE0 ? 0xA0 : 0x80;
            const unsigned char high = ch0 == 0xED ? 0x9F : 0xBF;
            if (ch1 < low || ch1 > high) {
                return false;
            }
            const unsigned char ch2 = *++p;
            if (ch2 < 0x80 || ch2 > 0xBF) {
                return false;
            }
            continue;
        }
        // 4 byte encoding: 0xF0..0xF3
        if (end <= &p[3]) {
            return false;
        }
        const unsigned char ch1 = *++p;
        const unsigned char low = ch0 == 0xF0 ? 0x90 : 0x80;
        const unsigned char high = ch0 == 0xF4 ? 0x8F : 0xBF;
        if (ch1 < low || ch1 > high) {
            return false;
        }
        const unsigned char ch2 = *++p;
        if (ch2 < 0x80 || ch2 > 0xBF) {
            return false;
        }
        const unsigned char ch3 = *++p;
        if (ch3 < 0x80 || ch3 > 0xBF) {
            return false;
        }
    }
    return true;
}

}  // namespace mk
