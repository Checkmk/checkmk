// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Filter.h"

std::optional<std::string> Filter::stringValueRestrictionFor(
    const std::string & /* column_name */) const {
    return {};
}

std::optional<int32_t> Filter::greatestLowerBoundFor(
    const std::string & /* column_name */,
    std::chrono::seconds /* timezone_offset */) const {
    return {};
}

std::optional<int32_t> Filter::leastUpperBoundFor(
    const std::string & /* column_name */,
    std::chrono::seconds /* timezone_offset */) const {
    return {};
}

std::optional<std::bitset<32>> Filter::valueSetLeastUpperBoundFor(
    const std::string & /* column_name */,
    std::chrono::seconds /* timezone_offset */) const {
    return {};
}
