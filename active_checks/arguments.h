// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef arguments_h
#define arguments_h

#include <cstdint>
#include <optional>
#include <string>
#include <utility>

namespace check_mkevents {

// Parses a number from 1 to max, digits only, unlike std::stoul().
std::optional<unsigned long> parse_number(const std::string &s,
                                          unsigned long max);

// Parses a port number from 1 to 65535.
std::optional<uint16_t> parse_port(const std::string &s);

// Parses "HOST[:PORT]" or "[IPV6]:PORT", ignoring extra colons around the port
// like the rule always did. An empty port means the default one. Without
// brackets, "cafe::6558" is an IPv6 address, "fe80::1%eth0:6558" has a port.
std::optional<std::pair<std::string, uint16_t>> parse_remote(
    const std::string &remote, uint16_t default_port);

}  // namespace check_mkevents

#endif  // arguments_h
