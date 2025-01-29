// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/AttributeListColumn.h"

#include <algorithm>
#include <bitset>
#include <cctype>
#include <map>
#include <string_view>
#include <utility>

#include "livestatus/Logger.h"

using namespace std::string_view_literals;

namespace column::attribute_list {

// see MODATTR_FOO in nagios/common.h
// NOLINTNEXTLINE(cert-err58-cpp)
const std::map<std::string_view, unsigned long> known_attributes = {
    {"notifications_enabled"sv, 0},    {"active_checks_enabled"sv, 1},
    {"passive_checks_enabled"sv, 2},   {"event_handler_enabled"sv, 3},
    {"flap_detection_enabled"sv, 4},   {"failure_prediction_enabled"sv, 5},
    {"performance_data_enabled"sv, 6}, {"obsessive_handler_enabled"sv, 7},
    {"event_handler_command"sv, 8},    {"check_command"sv, 9},
    {"normal_check_interval"sv, 10},   {"retry_check_interval"sv, 11},
    {"max_check_attempts"sv, 12},      {"freshness_checks_enabled"sv, 13},
    {"check_timeperiod"sv, 14},        {"custom_variable"sv, 15},
    {"notification_timeperiod"sv, 16}};

using modified_attributes = std::bitset<32>;

std::string refValueFor(const std::string &value, Logger *logger) {
    if (!value.empty() && std::isdigit(value[0]) != 0) {
        return value;
    }
    std::string_view val{value};
    modified_attributes values;
    while (!val.empty()) {
        auto attr = val.substr(0, val.find(','));
        val.remove_prefix(std::min(val.size(), attr.size() + 1));
        auto it = known_attributes.find(attr);
        if (it == known_attributes.end()) {
            Informational(logger)
                << "ignoring invalid value '" << attr << "' for attribute list";
            continue;
        }
        values[it->second] = true;
    }
    return std::to_string(values.to_ulong());
}

unsigned long decode(const std::vector<AttributeBit> &mask) {
    unsigned long out = 0;
    for (const auto &bit : mask) {
        out |= static_cast<int>(bit.value) << bit.index;
    }
    return out;
}

std::vector<AttributeBit> encode(unsigned long mask) {
    std::vector<AttributeBit> out;
    modified_attributes values{mask};
    out.reserve(values.size());
    for (std::size_t ii = 0; ii < values.size(); ++ii) {
        out.emplace_back(ii, values[ii]);
    }
    return out;
}

std::vector<AttributeBit> encode(const std::vector<std::string> &strs) {
    std::vector<AttributeBit> out;
    for (std::size_t ii = 0; ii < modified_attributes().size(); ++ii) {
        out.emplace_back(ii, false);
    }
    for (const auto &str : strs) {
        auto it = known_attributes.find(str);
        if (it != known_attributes.end()) {
            out[it->second].value = true;
        }
    }
    return out;
}

}  // namespace column::attribute_list

namespace column::detail {
template <>
std::string serialize(const column::attribute_list::AttributeBit &bit) {
    for (const auto &[k, v] : column::attribute_list::known_attributes) {
        if (v == bit.index && bit.value) {
            return std::string{k};
        }
    }
    return {};
}
}  // namespace column::detail
