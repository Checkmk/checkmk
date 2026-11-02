// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "active_checks/arguments.h"

#include <algorithm>
#include <cctype>

namespace check_mkevents {

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

}  // namespace check_mkevents
