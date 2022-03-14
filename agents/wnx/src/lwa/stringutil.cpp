#include "stdafx.h"

#include "stringutil.h"

#include <ws2tcpip.h>

#include <cassert>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <optional>
#include <regex>

#include "Logger.h"
#include "win_error.h"

#ifdef _WIN32
#endif

using std::string;
using std::wstring;

template <>
std::regex possiblyQuotedRegex<char>() {
    return std::regex{"(\"([^\"]+)\"|'([^']+)'|[^\" \\t]+)"};
}

template <>
std::wregex possiblyQuotedRegex<wchar_t>() {
    return std::wregex{L"(\"([^\"]+)\"|'([^']+)'|[^\" \\t]+)"};
}

int parse_boolean(const char *value) {
    if (!strcmp(value, "yes"))
        return 1;
    else if (!strcmp(value, "no"))
        return 0;
    else
        std::cerr << "Invalid boolean value. Only yes and no are allowed."
                  << std::endl;
    return -1;
}

bool ci_compare_pred(unsigned char lhs, unsigned char rhs) {
    return std::tolower(lhs) == std::tolower(rhs);
}

bool ci_equal(const std::string &lhs, const std::string &rhs) {
    return std::equal(lhs.cbegin(), lhs.cend(), rhs.cbegin(), rhs.cend(),
                      ci_compare_pred);
}

bool ci_compare(const std::string &lhs, const std::string &rhs) {
    for (auto ri = lhs.cbegin(), li = rhs.cbegin();
         ri != lhs.cend() && li != rhs.cend(); ++ri, ++li) {
        auto l1 = std::tolower(*ri), l2 = std::tolower(*li);
        if (l1 != l2) {
            return l1 < l2;
        }
    }

    // If equal until here, lhs < rhs iff lhs shorter than rhs.
    return lhs.size() < rhs.size();
}

// clang-format off
template <> char sol<char>() { return '^'; }
template <> wchar_t sol<wchar_t>() { return L'^'; }

template <> char eol<char>() { return '$'; }
template <> wchar_t eol<wchar_t>() { return L'$'; }

template <> char anyS<char>() { return '.'; }
template <> wchar_t anyS<wchar_t>() { return L'.'; }

template <> char anySGlob<char>() { return '?'; }
template <> wchar_t anySGlob<wchar_t>() { return L'?'; }

template <> char anyN<char>() { return '*'; }
template <> wchar_t anyN<wchar_t>() { return L'*'; }

template <> char esc<char>() { return '\\'; }
template <> wchar_t esc<wchar_t>() { return L'\\'; }
// clang-format on

template <>
bool needsEscape<char>(char c) {
    return std::string{"$()+.[]^{|}\\"}.find(c) != std::string::npos;
}
template <>
bool needsEscape<wchar_t>(wchar_t c) {
    return std::wstring{L"$()+.[]^{|}\\"}.find(c) != std::wstring::npos;
}

std::string replaceAll(const std::string &str, const std::string &from,
                       const std::string &to) {
    if (from.empty()) {
        return str;
    }

    std::string result(str);
    size_t pos = 0;

    while ((pos = result.find(from, pos)) != std::string::npos) {
        result.replace(pos, from.length(), to);
        pos += to.length();
    }
    return result;
}

void stringToIPv6(const char *value, uint16_t *address) {
    const char *pos = value;
    std::vector<uint16_t> segments;
    int skip_offset = -1;
    segments.reserve(8);

    while (pos != NULL) {
        char *endpos = NULL;
        unsigned long segment = strtoul(pos, &endpos, 16);

        if (segment > 0xFFFFu) {
            std::cerr << "Invalid ipv6 address " << value << std::endl;
            exit(1);
        } else if (endpos == pos) {
            skip_offset = static_cast<int>(segments.size());
        } else {
            segments.push_back((unsigned short)segment);
        }
        if (*endpos != ':') {
            break;
        }
        pos = endpos + 1;
        ++segment;
    }

    int idx = 0;
    for (std::vector<uint16_t>::const_iterator iter = segments.begin();
         iter != segments.end(); ++iter) {
        if (idx == skip_offset) {
            // example with ::42: segments.size() = 1
            //   this will fill the first 7 fields with 0 and increment idx by 7
            for (size_t i = 0; i < 8 - segments.size(); ++i) {
                address[idx + i] = 0;
            }
            idx += 8 - static_cast<int>(segments.size());
        }

        address[idx++] = ::htons(*iter);
        assert(idx <= 8);
    }
}

void stringToIPv4(const char *value, uint32_t &address) {
    unsigned a, b, c, d;
    if (4 != sscanf(value, "%u.%u.%u.%u", &a, &b, &c, &d)) {
        std::cerr << "Invalid value " << value << " for only_hosts"
                  << std::endl;
        exit(1);
    }

    address = a + b * 0x100 + c * 0x10000 + d * 0x1000000;
}

void netmaskFromPrefixIPv6(int bits, uint16_t *netmask) {
    memset(netmask, 0, sizeof(uint16_t) * 8);
    for (int i = 0; i < 8; ++i) {
        if (bits > 0) {
            int consume_bits = std::min(16, bits);
            netmask[i] = ::htons(0xFFFF << (16 - consume_bits));
            bits -= consume_bits;
        }
    }
}

void netmaskFromPrefixIPv4(int bits, uint32_t &netmask) {
    uint32_t mask_swapped = 0;
    for (int bit = 0; bit < bits; bit++) mask_swapped |= 0x80000000 >> bit;
    unsigned char *s = (unsigned char *)&mask_swapped;
    unsigned char *t = (unsigned char *)&netmask;
    t[3] = s[0];
    t[2] = s[1];
    t[1] = s[2];
    t[0] = s[3];
}

std::string IPAddrToString(const sockaddr_storage &addr) {
    std::vector<char> buffer(INET6_ADDRSTRLEN);
    unsigned short family = addr.ss_family;
    sockaddr const *inputAddr = nullptr;
    DWORD length = 0;

    switch (family) {
        case AF_INET: {
            const auto &s = reinterpret_cast<const sockaddr_in &>(addr);
            inputAddr = reinterpret_cast<sockaddr const *>(&s);
            length = sizeof(sockaddr_in);
            break;
        }
        case AF_INET6: {
            const auto &s = reinterpret_cast<const sockaddr_in6 &>(addr);
            inputAddr = reinterpret_cast<sockaddr const *>(&s);
            length = sizeof(sockaddr_in6);
            break;
        }
    }

    DWORD size = static_cast<DWORD>(buffer.size());
    if (::WSAAddressToString(const_cast<sockaddr *>(inputAddr), length, nullptr,
                             (LPWSTR)buffer.data(), &size) == SOCKET_ERROR) {
        int errorId = ::WSAGetLastError();
        XLOG::l() << "Cannot convert IPv" << (family == AF_INET ? "4" : "6")
                  << " address to string: " << get_win_error_as_string(errorId)
                  << " (" << errorId << ")";
    }

    return extractIPAddress(buffer.data());
}

namespace {

using OptionalString = std::optional<std::string>;
using MatchFunc = std::function<OptionalString(const std::string &)>;

const std::string ipv4seg{"[[:digit:]]{1,3}"};
const std::string ipv4startSeg{"[1-9][[:digit:]]{0,2}"};
const std::string ipv4addr{"(" + ipv4startSeg + "(\\." + ipv4seg + "){3})"};
const std::string ipv6seg{"[0-9a-fA-F]{1,4}"};
const std::string port{"[[:digit:]]+"};
const std::regex ipv4{"^" + ipv4addr + "(:" + port + ")?$"};

OptionalString matchBase(const std::string &input, const std::regex &reg) {
    std::smatch match;

    if (std::regex_match(input, match, reg) && match.size() >= 2) {
        return {match[1].str()};
    }

    return {};
}

OptionalString matchIPv4(const std::string &inputAddr) {
    return matchBase(inputAddr, ipv4);
}

OptionalString matchIPv6Mapped(const std::string &inputAddr) {
    const std::string ipv6addrMapped{"::(ffff(:0)?:)?(" + ipv4addr + ")"};
    const std::regex ipv6mapped{"^\\[?" + ipv6addrMapped + "(\\]:" + port +
                                ")?$"};
    std::smatch match;

    if (std::regex_match(inputAddr, match, ipv6mapped) && match.size() >= 2) {
        for (const auto &m : match) {
            const auto subString{m.str()};
            if (const auto subMatch = matchBase(subString, ipv4)) {
                return subMatch;
            }
        }
    }

    return {};
}

OptionalString matchIPv6(const std::string &inputAddr) {
    const std::string ipv6addr{
        "(" +                                                //
        ipv6seg + "(:" + ipv6seg + "){7}" +                  //
        "|(" + ipv6seg + ":){1,7}:" +                        //
        "|(" + ipv6seg + ":){1,6}:" + ipv6seg +              //
        "|(" + ipv6seg + ":){1,5}(:" + ipv6seg + "){1,2}" +  //
        "|(" + ipv6seg + ":){1,4}(:" + ipv6seg + "){1,3}" +  //
        "|(" + ipv6seg + ":){1,3}(:" + ipv6seg + "){1,4}" +  //
        "|(" + ipv6seg + ":){1,2}(:" + ipv6seg + "){1,5}" +  //
        "|" + ipv6seg + ":(:" + ipv6seg + "){1,6}" +         //
        "|:(:" + ipv6seg + "){1,7}" +                        //
        "|::" +                                              //
        ")"};
    const std::regex ipv6{"^\\[?" + ipv6addr + "(\\]:" + port + ")?$"};

    return matchBase(inputAddr, ipv6);
}

OptionalString matchIPv6Embedded(const std::string &inputAddr) {
    const std::string ipv6addrEmbedded{std::string{"("} + "(" + ipv6seg +
                                       ":){1,4}:" + ipv4addr + ")"};
    const std::regex ipv6embedded{"^\\[?" + ipv6addrEmbedded + "(\\]:" + port +
                                  ")?$"};

    return matchBase(inputAddr, ipv6embedded);
}

}  // namespace

std::string extractIPAddress(const std::string &inputAddr) {
    for (const MatchFunc &func :
         {matchIPv4, matchIPv6Mapped, matchIPv6, matchIPv6Embedded}) {
        if (const auto match = func(inputAddr)) {
            return match.value();
        }
    }

    return inputAddr;  // no match, return original input
}

std::string ConvertToUTF8(const std::wstring &Src) noexcept {
    using namespace std;

    if (Src.empty()) return {};
    // Windows only
    auto in_len = static_cast<int>(Src.length());
    auto out_len =
        ::WideCharToMultiByte(CP_UTF8, 0, Src.c_str(), in_len, NULL, 0, 0, 0);
    if (out_len == 0) return {};

    std::string str;
    try {
        str.resize(out_len);
    } catch (const std::exception &) {
        return {};
    }

    // convert
    ::WideCharToMultiByte(CP_UTF8, 0, Src.c_str(), -1, str.data(), out_len, 0,
                          0);
    return str;
}
