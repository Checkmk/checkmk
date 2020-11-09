// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DoubleFilter.h"

#include <cstdlib>
#include <ostream>

#include "DoubleColumn.h"
#include "Logger.h"
#include "Row.h"

DoubleFilter::DoubleFilter(Kind kind, const DoubleColumn &column,
                           RelationalOperator relOp, const std::string &value)
    : ColumnFilter(kind, column, relOp, value)
    , _column(column)
    , _ref_value(atof(value.c_str())) {}

bool DoubleFilter::accepts(Row row, const contact * /* auth_user */,
                           std::chrono::seconds /* timezone_offset */) const {
    double act_value = _column.getValue(row);
    switch (oper()) {
        case RelationalOperator::equal:
            return act_value == _ref_value;
        case RelationalOperator::not_equal:
            return act_value != _ref_value;
        case RelationalOperator::less:
            return act_value < _ref_value;
        case RelationalOperator::greater_or_equal:
            return act_value >= _ref_value;
        case RelationalOperator::greater:
            return act_value > _ref_value;
        case RelationalOperator::less_or_equal:
            return act_value <= _ref_value;
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            Informational(_column.logger())
                << "Sorry. Operator " << oper()
                << " for float columns not implemented.";
            return false;
    }
    return false;  // unreachable
}

std::unique_ptr<Filter> DoubleFilter::copy() const {
    return std::make_unique<DoubleFilter>(*this);
}

std::unique_ptr<Filter> DoubleFilter::negate() const {
    return std::make_unique<DoubleFilter>(
        kind(), _column, negateRelationalOperator(oper()), value());
}
