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

bool IntFilter::accepts(Row row, const contact *auth_user,
                        std::chrono::seconds /*timezone_offset*/) const {
    int32_t act_value = _column.getValue(row, auth_user);
    switch (oper()) {
        case RelationalOperator::equal:
            return act_value == _ref_value;
        case RelationalOperator::not_equal:
            return act_value != _ref_value;
        case RelationalOperator::matches:  // superset
            return (act_value & _ref_value) == _ref_value;
        case RelationalOperator::doesnt_match:  // not superset
            return (act_value & _ref_value) != _ref_value;
        case RelationalOperator::equal_icase:  // subset
            return (act_value & _ref_value) == act_value;
        case RelationalOperator::not_equal_icase:  // not subset
            return (act_value & _ref_value) != act_value;
        case RelationalOperator::matches_icase:  // contains any
            return (act_value & _ref_value) != 0;
        case RelationalOperator::doesnt_match_icase:  // contains none of
            return (act_value & _ref_value) == 0;
        case RelationalOperator::less:
            return act_value < _ref_value;
        case RelationalOperator::greater_or_equal:
            return act_value >= _ref_value;
        case RelationalOperator::greater:
            return act_value > _ref_value;
        case RelationalOperator::less_or_equal:
            return act_value <= _ref_value;
    }
    return false;  // unreachable
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
            return {};
    }
    return {};  // unreachable
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
            return {};
    }
    return {};  // unreachable
}

bool IntFilter::optimizeBitmask(
    const std::string &column_name, uint32_t *mask,
    std::chrono::seconds /*timezone_offset*/) const {
    if (column_name != columnName()) {
        return false;  // wrong column
    }

    if (_ref_value < 0 || _ref_value > 31) {
        return true;  // not optimizable by 32bit bit mask
    }

    // Our task is to remove those bits from mask that are deselected by the
    // filter.
    uint32_t bit = 1 << _ref_value;

    switch (oper()) {
        case RelationalOperator::equal:
            *mask &= bit;  // bit must be set
            return true;
        case RelationalOperator::not_equal:
            *mask &= ~bit;  // bit must not be set
            return true;
        case RelationalOperator::greater_or_equal:
            bit >>= 1;
        // fallthrough
        case RelationalOperator::greater:
            while (bit != 0u) {
                *mask &= ~bit;
                bit >>= 1;
            }
            return true;
        case RelationalOperator::less_or_equal:
            if (_ref_value == 31) {
                return true;
            }
            bit <<= 1;
        // fallthrough
        case RelationalOperator::less:
            while (true) {
                *mask &= ~bit;
                if (bit == 0x80000000) {
                    return true;
                }
                bit <<= 1;
            }
            return true;
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            return false;
    }
    return false;  // unreachable
}

std::unique_ptr<Filter> IntFilter::copy() const {
    return std::make_unique<IntFilter>(*this);
}

std::unique_ptr<Filter> IntFilter::negate() const {
    return std::make_unique<IntFilter>(
        kind(), _column, negateRelationalOperator(oper()), value());
}
