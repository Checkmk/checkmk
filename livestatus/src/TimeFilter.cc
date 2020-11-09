// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TimeFilter.h"

#include <cstdlib>

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
