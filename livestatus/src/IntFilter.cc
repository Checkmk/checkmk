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

#include "IntFilter.h"
#include <cstdlib>
#include "Filter.h"
#include "IntColumn.h"
#include "Row.h"

IntFilter::IntFilter(Kind kind, const IntColumn &column,
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

bool IntFilter::accepts(Row row, const contact *auth_user,
                        std::chrono::seconds /*timezone_offset*/) const {
    return eval(_column.getValue(row, auth_user), oper(), _ref_value);
}

std::optional<int32_t> IntFilter::greatestLowerBoundFor(
    const std::string &column_name,
    std::chrono::seconds /* timezone_offset */) const {
    if (column_name != columnName()) {
        return {};  // wrong column
    }
    switch (oper()) {
        case RelationalOperator::equal:
        case RelationalOperator::greater_or_equal:
            return {_ref_value};
        case RelationalOperator::greater:
            return {_ref_value + 1};
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:             // superset
        case RelationalOperator::doesnt_match:        // not superset
        case RelationalOperator::equal_icase:         // subset
        case RelationalOperator::not_equal_icase:     // not subset
        case RelationalOperator::matches_icase:       // contains any
        case RelationalOperator::doesnt_match_icase:  // contains none of
        case RelationalOperator::less:
        case RelationalOperator::less_or_equal:
            // NOTE: If we use the equivalent 'return {}' here and the other
            // std::nullopt occurences below, we run into g++/libstdc++ bug
            // https://gcc.gnu.org/bugzilla/show_bug.cgi?id=86465. :-/
            return std::nullopt;
    }
    return std::nullopt;  // unreachable
}

std::optional<int32_t> IntFilter::leastUpperBoundFor(
    const std::string &column_name,
    std::chrono::seconds /* timezone_offset */) const {
    if (column_name != columnName()) {
        return {};  // wrong column
    }
    switch (oper()) {
        case RelationalOperator::equal:
        case RelationalOperator::less_or_equal:
            return {_ref_value};
        case RelationalOperator::less:
            return {_ref_value - 1};
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:             // superset
        case RelationalOperator::doesnt_match:        // not superset
        case RelationalOperator::equal_icase:         // subset
        case RelationalOperator::not_equal_icase:     // not subset
        case RelationalOperator::matches_icase:       // contains any
        case RelationalOperator::doesnt_match_icase:  // contains none of
        case RelationalOperator::greater_or_equal:
        case RelationalOperator::greater:
            return std::nullopt;
    }
    return std::nullopt;  // unreachable
}

std::optional<std::bitset<32>> IntFilter::valueSetLeastUpperBoundFor(
    const std::string &column_name,
    std::chrono::seconds /* timezone_offset */) const {
    if (column_name != columnName()) {
        return {};  // wrong column
    }
    std::bitset<32> result;
    for (int32_t bit = 0; bit < 32; ++bit) {
        result[bit] = eval(bit, oper(), _ref_value);
    }
    return {result};
}

std::unique_ptr<Filter> IntFilter::copy() const {
    return std::make_unique<IntFilter>(*this);
}

std::unique_ptr<Filter> IntFilter::negate() const {
    return std::make_unique<IntFilter>(
        kind(), _column, negateRelationalOperator(oper()), value());
}
