// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "AttributeListColumnUtils.h"

#include <bitset>
#include <cctype>
#include <map>
#include <utility>
#include <vector>

#include "Logger.h"
#include "strutil.h"

namespace column::attribute_list {

namespace {

// see MODATTR_FOO in nagios/common.h
const std::map<std::string, unsigned long> known_attributes = {
    {"notifications_enabled", 0},    {"active_checks_enabled", 1},
    {"passive_checks_enabled", 2},   {"event_handler_enabled", 3},
    {"flap_detection_enabled", 4},   {"failure_prediction_enabled", 5},
    {"performance_data_enabled", 6}, {"obsessive_handler_enabled", 7},
    {"event_handler_command", 8},    {"check_command", 9},
    {"normal_check_interval", 10},   {"retry_check_interval", 11},
    {"max_check_attempts", 12},      {"freshness_checks_enabled", 13},
    {"check_timeperiod", 14},        {"custom_variable", 15},
    {"notification_timeperiod", 16}};

using modified_attributes = std::bitset<32>;
}  // namespace

std::string refValueFor(const std::string &value, Logger *logger) {
    if (isdigit(value[0]) != 0) {
        return value;
    }

    std::vector<char> value_vec(value.begin(), value.end());
    value_vec.push_back('\0');
    char *scan = &value_vec[0];

    modified_attributes values;
    for (const char *t = nullptr; (t = next_token(&scan, ',')) != nullptr;) {
        auto it = known_attributes.find(t);
        if (it == known_attributes.end()) {
            Informational(logger)
                << "Ignoring invalid value '" << t << "' for attribute list";
            continue;
        }
        values[it->second] = true;
    }
    return std::to_string(values.to_ulong());
}

std::vector<std::string> decode(unsigned long mask) {
    std::vector<std::string> attributes;
    modified_attributes values(mask);
    for (const auto &entry : known_attributes) {
        if (values[entry.second]) {
            attributes.push_back(entry.first);
        }
    }
    return attributes;
}

}  // namespace column::attribute_list
