#include "types.h"
#include <algorithm>
#include <cstring>
#include <sstream>
#include <string>
#include "Environment.h"
#include "stringutil.h"

template <>
bool from_string<bool>(const WinApiInterface &, const std::string &value) {
    return parse_boolean(value.c_str());
}

template <>
int from_string<int>(const WinApiInterface &, const std::string &value) {
    return std::stol(value);
}

template <>
std::string from_string<std::string>(const WinApiInterface &,
                                     const std::string &value) {
    return value;
}

template <>
fs::path from_string<fs::path>(const WinApiInterface &,
                               const std::string &value) {
    return {value};
}

template <>
ipspec from_string<ipspec>(const WinApiInterface &winapi,
                           const std::string &value) {
    ipspec result{winapi};

    auto slash_pos = strchr(value.c_str(), '/');
    if (slash_pos != NULL) {
        // ipv4/ipv6 agnostic
        result.bits = strtol(slash_pos + 1, NULL, 10);
    } else {
        result.bits = 0;
    }

    result.ipv6 = strchr(value.c_str(), ':') != NULL;

    if (result.ipv6) {
        if (result.bits == 0) {
            result.bits = 128;
        }
        stringToIPv6(value.c_str(), result.ip.v6.address, winapi);
        netmaskFromPrefixIPv6(result.bits, result.ip.v6.netmask, winapi);

        // TODO verify that host part is 0
    } else {
        if (result.bits == 0) {
            result.bits = 32;
        }

        stringToIPv4(value.c_str(), result.ip.v4.address);
        netmaskFromPrefixIPv4(result.bits, result.ip.v4.netmask);

        if ((result.ip.v4.address & result.ip.v4.netmask) !=
            result.ip.v4.address) {
            std::cerr << "Invalid only_hosts entry: host part not 0: " << value
                      << std::endl;
            exit(1);
        }
    }
    return result;
}

std::ostream &operator<<(std::ostream &os, const ipspec &ips) {
    if (ips.ipv6) {
        std::array<uint16_t, 8> hostByteAddress = {0};
        std::transform(ips.ip.v6.address, ips.ip.v6.address + 8,
                       hostByteAddress.begin(),
                       [&ips](const uint16_t netshort) {
                           return ips.winapi.get().ntohs(netshort);
                       });
        os << join(hostByteAddress.cbegin(), hostByteAddress.cend(), ":",
                   std::ios::hex)
           << "/" << ips.bits;
    } else {
        os << (ips.ip.v4.address & 0xff) << "."
           << (ips.ip.v4.address >> 8 & 0xff) << "."
           << (ips.ip.v4.address >> 16 & 0xff) << "."
           << (ips.ip.v4.address >> 24 & 0xff) << "/" << ips.bits;
    }

    return os;
}

ipspec toIPv6(const ipspec &ips, const WinApiInterface &winapi) {
    ipspec result{winapi};
    // first 96 bits are fixed: 0:0:0:0:0:ffff
    result.bits = 96 + ips.bits;
    result.ipv6 = true;

    uint32_t ipv4_loopback = 0;
    stringToIPv4("127.0.0.1", ipv4_loopback);

    // For IPv4 loopback address 127.0.0.1, add corresponding IPv6
    // loopback address 0:0:0:0:0:0:0:1 (also known as ::1).
    if (ips.ip.v4.address == ipv4_loopback) {
        memset(result.ip.v6.address, 0, sizeof(uint16_t) * 7);
        result.ip.v6.address[7] = winapi.htons(0x1);
    } else {
        memset(result.ip.v6.address, 0, sizeof(uint16_t) * 5);
        result.ip.v6.address[5] = 0xFFFFu;
        result.ip.v6.address[6] =
            static_cast<uint16_t>(ips.ip.v4.address & 0xFFFFu);
        result.ip.v6.address[7] =
            static_cast<uint16_t>(ips.ip.v4.address >> 16);
    }

    netmaskFromPrefixIPv6(result.bits, result.ip.v6.netmask, winapi);

    return result;
}
