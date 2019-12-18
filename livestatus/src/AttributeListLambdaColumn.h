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

#ifndef AttributeListLambdaColumn_h
#define AttributeListLambdaColumn_h

#include "config.h"  // IWYU pragma: keep
#include <functional>
#include <string>
#include "AttributeListAsIntColumn.h"
#include "ListColumn.h"

// TODO(ml): This could likely be simplified with a dict column.
//
//           See also
//             - `TableContacts::GetCustomAttribute` and
//             - `TableContacts::GetCustomAttributeElem`
//           for an example of a dict column without pointer arithmetic.

class AttributeBitmaskLambdaColumn : public AttributeListAsIntColumn {
public:
    AttributeBitmaskLambdaColumn(std::string name, std::string description,
                                 std::function<int(Row)> f)
        : AttributeListAsIntColumn(std::move(name), std::move(description), {})
        , get_value_{f} {}
    virtual ~AttributeBitmaskLambdaColumn() = default;
    std::int32_t getValue(Row row,
                          const contact * /*auth_user*/) const override {
        return getValue(row);
    }
    std::int32_t getValue(Row row) const { return get_value_(row); }

private:
    std::function<int(Row)> get_value_;
};

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

using modified_attributes = std::bitset<32>;
}  // namespace

class AttributeListColumn2 : public ListColumn {
public:
    AttributeListColumn2(std::string name, std::string description,
                         AttributeBitmaskLambdaColumn bitmask_col)
        : ListColumn(std::move(name), std::move(description), {})
        , bitmask_col_{std::move(bitmask_col)} {}

    std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return bitmask_col_.createFilter(kind, relOp, value);
    }
    std::vector<std::string> getValue(
        Row row, const contact * /*auth_user*/,
        std::chrono::seconds /*timezone_offset*/) const override {
        return getValue(row);
    }
    std::vector<std::string> getValue(Row row) const {
        std::vector<std::string> attrs;
        modified_attributes values(bitmask_col_.getValue(row));
        for (const auto &entry : known_attributes) {
            if (values[entry.second]) {
                attrs.push_back(entry.first);
            }
        }
        return attrs;
    }

private:
    AttributeBitmaskLambdaColumn bitmask_col_;
};

#endif
