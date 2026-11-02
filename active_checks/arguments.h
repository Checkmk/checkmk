// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef arguments_h
#define arguments_h

#include <cstdint>
#include <optional>
#include <string>

namespace check_mkevents {

// Parses a number from 1 to max, digits only, unlike std::stoul().
std::optional<unsigned long> parse_number(const std::string &s,
                                          unsigned long max);

// Parses a port number from 1 to 65535.
std::optional<uint16_t> parse_port(const std::string &s);

}  // namespace check_mkevents

#endif  // arguments_h
