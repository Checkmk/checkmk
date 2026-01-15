// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/StringUtils.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <cerrno>
#include <cstdlib>
#include <iomanip>
#include <sstream>
#include <stdexcept>

#include "livestatus/OStreamStateSaver.h"

namespace mk {
std::string unsafe_tolower(const std::string &str) {
    std::string result = str;
    std::ranges::transform(str, result.begin(), ::tolower);
    return result;
}

std::string unsafe_toupper(const std::string &str) {
    std::string result = str;
    std::ranges::transform(str, result.begin(), ::toupper);
    return result;
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
               : std::make_pair(
                     mk::rstrip(composite_key.substr(0, semicolon)),
                     mk::rstrip(composite_key.substr(semicolon + 1)));
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

std::ostream &operator<<(std::ostream &os, const escape_nonprintable &enp) {
    const OStreamStateSaver s{os};
    os << std::hex << std::uppercase << std::setfill('0');
    for (auto ch : enp.buffer) {
        const int uch{static_cast<unsigned char>(ch)};
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
    const size_t match = str.find(from);
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
    const size_t added_after_match = from.empty() ? 1 : 0;
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

std::string replace_chars(const std::string &str,
                          const std::string &chars_to_replace,
                          char replacement) {
    std::string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars_to_replace, i)) !=
           std::string::npos) {
        result[i++] = replacement;
    }
    return result;
}

std::string ipAddressToString(const in_addr &address) {
    std::array<char, INET_ADDRSTRLEN> addr_buf{};
    inet_ntop(AF_INET, &address, addr_buf.data(), addr_buf.size());
    return addr_buf.data();
}

std::string ipAddressToString(const in6_addr &address) {
    std::array<char, INET6_ADDRSTRLEN> addr_buf{};
    inet_ntop(AF_INET6, &address, addr_buf.data(), addr_buf.size());
    return addr_buf.data();
}
namespace ec {
// The funny encoding of an Iterable[str] | None is done in
// cmk.ec.history.quote_tab().

bool is_none(const std::string &str) { return str == "\002"; }

std::vector<std::string> split_list(const std::string &str) {
    return str.empty() || is_none(str) ? std::vector<std::string>()
                                       : mk::split(str.substr(1), '\001');
}

}  // namespace ec

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
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
    // NOLINTBEGIN(cppcoreguidelines-pro-bounds-pointer-arithmetic)
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
        // NOLINTEND(cppcoreguidelines-pro-bounds-pointer-arithmetic)
        if (ch3 < 0x80 || ch3 > 0xBF) {
            return false;
        }
    }
    return true;
}

void skip_whitespace(std::string_view &str) {
    str.remove_prefix(
        std::min(str.size(), str.find_first_not_of(mk::whitespace)));
}

std::string next_argument(std::string_view &str) {
    skip_whitespace(str);
    if (str.empty()) {
        throw std::runtime_error("missing argument");
    }
    constexpr auto quote = '\'';
    if (!str.starts_with(quote)) {
        std::string result{str.substr(0, str.find_first_of(mk::whitespace))};
        str.remove_prefix(result.size());
        return result;
    }
    std::string result;
    while (true) {
        str.remove_prefix(1);
        auto pos = str.find(quote);
        if (pos == std::string_view::npos) {
            throw std::runtime_error("missing closing quote");
        }
        result += str.substr(0, pos);
        str.remove_prefix(pos + 1);
        if (!str.starts_with(quote)) {
            return result;
        }
        result += quote;
    }
}

std::pair<char *, std::error_code> from_chars(const char *first,
                                              const char * /* last */,
                                              double &value) {
    errno = 0;
    char dummy = '\0';
    // False positive of misc-const-correctness.AnalyzePointers, see e.g.
    // https://github.com/llvm/llvm-project/issues/157320
    // NOLINTNEXTLINE(misc-const-correctness)
    char *end = &dummy;  // must not be nullptr
    value = strtod(first, &end);
    if (end == first) {
        // any non-zero error will do for now
        return std::make_pair(
            end, std::make_error_code(std::errc::illegal_byte_sequence));
    }
    return std::make_pair(end, std::make_error_code(std::errc{errno}));
}
}  // namespace mk
