// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "active_checks/arguments.h"

#include <arpa/inet.h>
#include <netinet/in.h>

#include <algorithm>
#include <cctype>
#include <string_view>

namespace check_mkevents {

namespace {

// Whether it's a zone like "eth0" in "fe80::1%eth0", made of the unreserved
// characters of URIs (RFC 6874), so without colons or brackets.
bool is_zone(std::string_view zone) {
    return !zone.empty() && std::ranges::all_of(zone, [](unsigned char c) {
        return std::isalnum(c) != 0 || c == '-' || c == '.' || c == '_' ||
               c == '~';
    });
}

// Whether it's an IPv6 address, maybe with a zone like in "fe80::1%eth0".
bool is_ipv6_address(const std::string &address) {
    const auto percent = address.find('%');
    in6_addr parsed{};
    return inet_pton(AF_INET6, address.substr(0, percent).c_str(), &parsed) ==
               1 &&
           (percent == std::string::npos ||
            is_zone(std::string_view{address}.substr(percent + 1)));
}

// The longest IPv6 address followed by colons only, e.g. "2001:db8::" in
// "2001:db8:::", where only the last colon is left for an empty port.
std::optional<std::string> ipv6_address_before_colons(
    const std::string &remote) {
    auto end = remote.size();
    while (end > 0 && remote[end - 1] == ':') {
        end--;
        if (is_ipv6_address(remote.substr(0, end))) {
            return remote.substr(0, end);
        }
    }
    return {};
}

}  // namespace

std::optional<unsigned long> parse_number(const std::string &s,
                                          unsigned long max) {
    if (!std::ranges::all_of(
            s, [](unsigned char c) { return std::isdigit(c) != 0; })) {
        return {};
    }
    const auto digits = s.substr(std::min(s.find_first_not_of('0'), s.size()));
    if (digits.empty() || digits.size() > std::to_string(max).size()) {
        return {};
    }
    const auto number =
        std::stoul(digits);  // can't throw for a max below 10^19
    if (number > max) {
        return {};
    }
    return number;
}

std::optional<uint16_t> parse_port(const std::string &s) {
    const auto port = parse_number(s, 65535);
    return port ? std::optional{static_cast<uint16_t>(*port)} : std::nullopt;
}

std::optional<std::pair<std::string, uint16_t>> parse_remote(
    const std::string &remote, uint16_t default_port) {
    std::string address;
    std::string rest;  // empty or colons, maybe with a port among them
    // A zone ends at a colon. Without a zone, find() starts at npos and finds
    // no colon.
    const auto ipv6_end =
        std::min(remote.find(':', remote.find('%')), remote.size());
    if (remote.starts_with('[')) {
        const auto bracket = remote.find(']');
        if (bracket == std::string::npos ||
            !is_ipv6_address(remote.substr(1, bracket - 1))) {
            return {};
        }
        address = remote.substr(1, bracket - 1);
        rest = remote.substr(bracket + 1);
    } else if (is_ipv6_address(remote.substr(0, ipv6_end))) {
        address = remote.substr(0, ipv6_end);
        rest = remote.substr(ipv6_end);
    } else if (const auto ipv6 = ipv6_address_before_colons(remote)) {
        address = *ipv6;
        rest = remote.substr(address.size());
    } else {
        const auto colon = std::min(remote.find(':'), remote.size());
        address = remote.substr(0, colon);
        rest = remote.substr(colon);
    }
    if (!rest.empty() && !rest.starts_with(':')) {
        return {};
    }
    const auto first = rest.find_first_not_of(':');
    const auto port = first == std::string::npos
                          ? std::optional{default_port}
                          : parse_port(rest.substr(
                                first, rest.find_last_not_of(':') + 1 - first));
    if (address.empty() || !port) {
        return {};
    }
    return std::pair{address, *port};
}

}  // namespace check_mkevents
