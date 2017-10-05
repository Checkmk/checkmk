// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "AttributeListColumn.h"
#include <bitset>
#include <cctype>
#include <map>
#include <memory>
#include <ostream>
#include <utility>
#include <vector>
#include "Filter.h"
#include "IntFilter.h"
#include "Logger.h"
#include "Renderer.h"
#include "Row.h"
#include "strutil.h"

namespace {
// see MODATTR_FOO in nagios/common.h
std::map<std::string, unsigned long> known_attributes = {
    {"notifications_enabled", 0},    {"active_checks_enabled", 1},
    {"passive_checks_enabled", 2},   {"event_handler_enabled", 3},
    {"flap_detection_enabled", 4},   {"failure_prediction_enabled", 5},
    {"performance_data_enabled", 6}, {"obsessive_handler_enabled", 7},
    {"event_handler_command", 8},    {"check_command", 9},
    {"normal_check_interval", 10},   {"retry_check_interval", 11},
    {"max_check_attempts", 12},      {"freshness_checks_enabled", 13},
    {"check_timeperiod", 14},        {"custom_variable", 15},
    {"notification_timeperiod", 16}};

using modified_atttibutes = std::bitset<32>;
}  // namespace

int32_t AttributeListColumn::getValue(Row row,
                                      const contact * /*unused*/) const {
    if (auto p = columnData<void>(row)) {
        return static_cast<int32_t>(*offset_cast<unsigned long>(p, _offset));
    }
    return 0;
}

void AttributeListColumn::output(Row row, RowRenderer &r,
                                 const contact * /* auth_user */) const {
    ListRenderer l(r);
    modified_atttibutes values(getValue(row, nullptr));
    for (const auto &entry : known_attributes) {
        if (values[entry.second]) {
            l.output(entry.first);
        }
    }
}

std::unique_ptr<Filter> AttributeListColumn::createFilter(
    RelationalOperator relOp, const std::string &value) const {
    return std::make_unique<IntFilter>(*this, relOp,
                                       refValueFor(value, logger()));
}

// static
std::string AttributeListColumn::refValueFor(const std::string &value,
                                             Logger *logger) {
    if (isdigit(value[0]) != 0) {
        return value;
    }

    std::vector<char> value_vec(value.begin(), value.end());
    value_vec.push_back('\0');
    char *scan = &value_vec[0];

    modified_atttibutes values;
    for (const char *t; (t = next_token(&scan, ',')) != nullptr;) {
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
