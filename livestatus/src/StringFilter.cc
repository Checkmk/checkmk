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

#include "StringFilter.h"
#include <algorithm>
#include "Filter.h"
#include "RegExp.h"
#include "Row.h"
#include "StringColumn.h"

StringFilter::StringFilter(const StringColumn &column, RelationalOperator relOp,
                           std::string value)
    : _column(column)
    , _relOp(relOp)
    , _value(std::move(value))
    , _regExp(makeRegExpFor(_relOp, _value)) {}

bool StringFilter::accepts(Row row, const contact * /* auth_user */,
                           std::chrono::seconds /* timezone_offset */) const {
    std::string act_string = _column.getValue(row);
    switch (_relOp) {
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
            return act_string < _value;
        case RelationalOperator::greater_or_equal:
            return act_string >= _value;
        case RelationalOperator::greater:
            return act_string > _value;
        case RelationalOperator::less_or_equal:
            return act_string <= _value;
    }
    return false;  // unreachable
}

const std::string *StringFilter::stringValueRestrictionFor(
    const std::string &column_name) const {
    switch (_relOp) {
        case RelationalOperator::equal:
            return column_name == columnName() ? &_value : nullptr;
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
            return nullptr;
    }
    return nullptr;  // unreachable
}

std::unique_ptr<Filter> StringFilter::copy() const {
    return std::make_unique<StringFilter>(*this);
}

std::unique_ptr<Filter> StringFilter::negate() const {
    return std::make_unique<StringFilter>(
        _column, negateRelationalOperator(_relOp), _value);
}

std::string StringFilter::columnName() const { return _column.name(); }
