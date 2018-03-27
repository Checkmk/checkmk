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

#include "CustomVarsDictFilter.h"
#include <tuple>
#include <unordered_map>
#include <utility>
#include "CustomVarsDictColumn.h"
#include "Filter.h"
#include "RegExp.h"
#include "Row.h"
#include "StringUtils.h"

CustomVarsDictFilter::CustomVarsDictFilter(Kind kind,
                                           const CustomVarsDictColumn &column,
                                           RelationalOperator relOp,
                                           const std::string &value)
    : ColumnFilter(kind, column, relOp, value), _column(column) {
    // Filter for custom_variables:
    //    Filter: custom_variables = PATH /hirni.mk
    // The variable name is part of the value and separated with spaces
    std::tie(_ref_varname, _ref_string) = mk::nextField(value);
    _ref_string = mk::lstrip(_ref_string);
    _regExp = makeRegExpFor(oper(), _ref_string);
}

bool CustomVarsDictFilter::accepts(
    Row row, const contact * /* auth_user */,
    std::chrono::seconds /* timezone_offset */) const {
    auto cvm = _column.getValue(row);
    auto it = cvm.find(_ref_varname);
    auto act_string = it == cvm.end() ? "" : it->second;
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
            return act_string < _ref_string;
        case RelationalOperator::greater_or_equal:
            return act_string >= _ref_string;
        case RelationalOperator::greater:
            return act_string > _ref_string;
        case RelationalOperator::less_or_equal:
            return act_string <= _ref_string;
    }
    return false;  // unreachable
}

std::unique_ptr<Filter> CustomVarsDictFilter::copy() const {
    return std::make_unique<CustomVarsDictFilter>(*this);
}

std::unique_ptr<Filter> CustomVarsDictFilter::negate() const {
    return std::make_unique<CustomVarsDictFilter>(
        kind(), _column, negateRelationalOperator(oper()), value());
}
