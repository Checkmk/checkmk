// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "IntFilter.h"

#include <cstdlib>
#include <stdexcept>
#include <utility>

#include "Row.h"
#include "auth.h"

IntFilter::IntFilter(Kind kind, std::string columnName, function_type f,
                     RelationalOperator relOp, const std::string &value)
    : ColumnFilter{kind, std::move(columnName), relOp, value}
    , f_{std::move(f)}
    , _ref_value{atoi(value.c_str())} {}

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

bool IntFilter::accepts(Row row, const User &user,
                        std::chrono::seconds /*timezone_offset*/) const {
    if (std::holds_alternative<f0_t>(f_)) {
        return eval(std::get<f0_t>(f_)(row), oper(), _ref_value);
    }
    if (std::holds_alternative<f1_t>(f_)) {
        return eval(std::get<f1_t>(f_)(row, user.authUser()), oper(),
                    _ref_value);
    }
    throw std::runtime_error("unreachable");
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
        kind(), columnName(), f_, negateRelationalOperator(oper()), value());
}
