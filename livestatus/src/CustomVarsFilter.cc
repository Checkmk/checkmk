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

#include "CustomVarsFilter.h"
#include <algorithm>
#include <cstring>
#include <sstream>
#include <tuple>
#include "Column.h"
#include "CustomVarsColumn.h"
#include "Logger.h"
#include "StringUtils.h"

using mk::lstrip;
using mk::nextField;
using std::move;
using std::regex;
using std::regex_search;
using std::string;
using std::tie;

CustomVarsFilter::CustomVarsFilter(CustomVarsColumn *column,
                                   RelationalOperator relOp, string value)
    : _column(column), _relOp(relOp), _ref_text(move(value)) {
    if (_column->type() != ColumnType::dict) {
        return;
    }
    // Filter for custom_variables:
    //    Filter: custom_variables = PATH /hirni.mk
    // The variable name is part of the value and separated with spaces
    tie(_ref_varname, _ref_string) = nextField(_ref_text);
    _ref_string = lstrip(_ref_string);

    // Prepare regular expression
    switch (_relOp) {
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            _regex.assign(_ref_string,
                          (_relOp == RelationalOperator::matches_icase ||
                           _relOp == RelationalOperator::doesnt_match_icase)
                              ? regex::extended | regex::icase
                              : regex::extended);
            break;
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::less:
        case RelationalOperator::greater_or_equal:
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
            break;
    }
}

bool CustomVarsFilter::accepts(void *row, contact * /* auth_user */,
                               int /* timezone_offset */) {
    if (_column->type() == ColumnType::dict) {
        string act_string = _column->getVariable(row, _ref_varname);
        switch (_relOp) {
            case RelationalOperator::equal:
                return act_string == _ref_string;
            case RelationalOperator::not_equal:
                return act_string != _ref_string;
            case RelationalOperator::matches:
            case RelationalOperator::matches_icase:
                return regex_search(act_string, _regex);
            case RelationalOperator::doesnt_match:
            case RelationalOperator::doesnt_match_icase:
                return !regex_search(act_string, _regex);
            case RelationalOperator::equal_icase:
                return strcasecmp(_ref_string.c_str(), act_string.c_str()) == 0;
            case RelationalOperator::not_equal_icase:
                return strcasecmp(_ref_string.c_str(), act_string.c_str()) != 0;
            case RelationalOperator::less:
                return act_string < _ref_string;
            case RelationalOperator::greater_or_equal:
                return act_string >= _ref_string;
            case RelationalOperator::greater:
                return act_string > _ref_string;
            case RelationalOperator::less_or_equal:
                return act_string <= _ref_string;
        }
    }
    bool is_member = _column->contains(row, _ref_text);
    switch (_relOp) {
        case RelationalOperator::less:
            return !is_member;
        case RelationalOperator::greater_or_equal:
            return is_member;
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
            Informational(_logger)
                << "Sorry. Operator " << _relOp
                << " for custom variable list columns not implemented.";
            return false;
    }
    return false;  // unreachable
}

CustomVarsColumn *CustomVarsFilter::column() { return _column; }
