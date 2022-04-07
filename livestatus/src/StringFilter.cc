// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "StringFilter.h"

#include <utility>

#include "RegExp.h"
#include "Row.h"

StringFilter::StringFilter(Kind kind, std::string columnName,
                           std::function<std::string(Row)> getValue,
                           RelationalOperator relOp, const std::string &value)
    : ColumnFilter(kind, std::move(columnName), relOp, value)
    , _getValue{std::move(getValue)}
    , _regExp(makeRegExpFor(relOp, value)) {}

bool StringFilter::accepts(Row row, const User & /*user*/,
                           std::chrono::seconds /*timezone_offset*/) const {
    std::string act_string = _getValue(row);
    switch (oper()) {
        case RelationalOperator::equal:
        case RelationalOperator::equal_icase:
            return _regExp->match(act_string);
        case RelationalOperator::not_equal:
        case RelationalOperator::not_equal_icase:
            return !_regExp->match(act_string);
        case RelationalOperator::matches:
        case RelationalOperator::matches_icase:
            return _regExp->search(act_string);
        case RelationalOperator::doesnt_match:
        case RelationalOperator::doesnt_match_icase:
            return !_regExp->search(act_string);
            // FIXME: The cases below are nonsense for UTF-8...
        case RelationalOperator::less:
            return act_string < value();
        case RelationalOperator::greater_or_equal:
            return act_string >= value();
        case RelationalOperator::greater:
            return act_string > value();
        case RelationalOperator::less_or_equal:
            return act_string <= value();
    }
    return false;  // unreachable
}

std::optional<std::string> StringFilter::stringValueRestrictionFor(
    const std::string &column_name) const {
    if (column_name != columnName()) {
        return {};  // wrong column
    }
    switch (oper()) {
        case RelationalOperator::equal:
            return {value()};
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
        case RelationalOperator::less:
        case RelationalOperator::greater_or_equal:
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
            return {};
    }
    return {};  // unreachable
}

std::unique_ptr<Filter> StringFilter::copy() const {
    return std::make_unique<StringFilter>(*this);
}

std::unique_ptr<Filter> StringFilter::negate() const {
    return std::make_unique<StringFilter>(kind(), columnName(), _getValue,
                                          negateRelationalOperator(oper()),
                                          value());
}
