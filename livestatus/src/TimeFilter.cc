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

#include "TimeFilter.h"
#include <cstdlib>
#include "Filter.h"
#include "Row.h"
#include "TimeColumn.h"

TimeFilter::TimeFilter(Kind kind, const TimeColumn &column,
                       RelationalOperator relOp, const std::string &value)
    : ColumnFilter(kind, column, relOp, value)
    , _column(column)
    , _ref_value(atoi(value.c_str())) {}

namespace {
bool eval(int32_t x, RelationalOperator op, int32_t y) {
    switch (op) {
        case RelationalOperator::equal:
            return x == y;
        case RelationalOperator::not_equal:
            return x != y;
        case RelationalOperator::matches:  // superset
            return (x & y) == y;
        case RelationalOperator::doesnt_match:  // not superset
            return (x & y) != y;
        case RelationalOperator::equal_icase:  // subset
            return (x & y) == x;
        case RelationalOperator::not_equal_icase:  // not subset
            return (x & y) != x;
        case RelationalOperator::matches_icase:  // contains any
            return (x & y) != 0;
        case RelationalOperator::doesnt_match_icase:  // contains none of
            return (x & y) == 0;
        case RelationalOperator::less:
            return x < y;
        case RelationalOperator::greater_or_equal:
            return x >= y;
        case RelationalOperator::greater:
            return x > y;
        case RelationalOperator::less_or_equal:
            return x <= y;
    }
    return false;
}
}  // namespace

bool TimeFilter::accepts(Row row, const contact * /*auth_user*/,
                         std::chrono::seconds timezone_offset) const {
    return eval(std::chrono::system_clock::to_time_t(
                    _column.getValue(row, timezone_offset)),
                oper(), _ref_value);
}

std::optional<int32_t> TimeFilter::greatestLowerBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    if (column_name != columnName()) {
        return {};  // wrong column
    }
    int32_t ref_value = _ref_value - timezone_offset.count();
    switch (oper()) {
        case RelationalOperator::equal:
        case RelationalOperator::greater_or_equal:
            return {ref_value};
        case RelationalOperator::greater:
            return {ref_value + 1};
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:             // superset
        case RelationalOperator::doesnt_match:        // not superset
        case RelationalOperator::equal_icase:         // subset
        case RelationalOperator::not_equal_icase:     // not subset
        case RelationalOperator::matches_icase:       // contains any
        case RelationalOperator::doesnt_match_icase:  // contains none of
        case RelationalOperator::less:
        case RelationalOperator::less_or_equal:
            return {};
    }
    return {};  // unreachable
}

std::optional<int32_t> TimeFilter::leastUpperBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    if (column_name != columnName()) {
        return {};  // wrong column
    }
    int32_t ref_value = _ref_value - timezone_offset.count();
    switch (oper()) {
        case RelationalOperator::equal:
        case RelationalOperator::less_or_equal:
            return {ref_value};
        case RelationalOperator::less:
            return {ref_value - 1};
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:             // superset
        case RelationalOperator::doesnt_match:        // not superset
        case RelationalOperator::equal_icase:         // subset
        case RelationalOperator::not_equal_icase:     // not subset
        case RelationalOperator::matches_icase:       // contains any
        case RelationalOperator::doesnt_match_icase:  // contains none of
        case RelationalOperator::greater_or_equal:
        case RelationalOperator::greater:
            return {};
    }
    return {};  // unreachable
}

std::optional<std::bitset<32>> TimeFilter::valueSetLeastUpperBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    if (column_name != columnName()) {
        return {};  // wrong column
    }
    std::bitset<32> result;
    for (int32_t bit = 0; bit < 32; ++bit) {
        result[bit] = eval(bit, oper(), _ref_value - timezone_offset.count());
    }
    return {result};
}

std::unique_ptr<Filter> TimeFilter::copy() const {
    return std::make_unique<TimeFilter>(*this);
}

std::unique_ptr<Filter> TimeFilter::negate() const {
    return std::make_unique<TimeFilter>(
        kind(), _column, negateRelationalOperator(oper()), value());
}
