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
#include <ctype.h>
#include <string.h>
#include <ostream>
#include "Column.h"
#include "CustomVarsColumn.h"
#include "Logger.h"
#include "OutputBuffer.h"

using std::string;

CustomVarsFilter::CustomVarsFilter(Query *query, CustomVarsColumn *column,
                                   RelationalOperator relOp,
                                   const string &value)
    : ColumnFilter(query)
    , _column(column)
    , _relOp(relOp)
    , _ref_text(value)
    , _regex(nullptr) {
    if (_column->type() != ColumnType::dict) {
        return;
    }
    // Filter for custom_variables:
    //    Filter: custom_variables = PATH /hirni.mk
    // The variable name is part of the value and separated with spaces
    const char *cstr = _ref_text.c_str();
    const char *search_space = cstr;
    while ((*search_space != 0) && (isspace(*search_space) == 0)) {
        search_space++;
    }
    _ref_varname = string(cstr, search_space - cstr);
    while ((*search_space != 0) && (isspace(*search_space) != 0)) {
        search_space++;
    }
    _ref_string = search_space;

    // Prepare regular expression
    switch (_relOp) {
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            if (strchr(search_space, '{') != nullptr ||
                strchr(search_space, '}') != nullptr) {
                setError(OutputBuffer::ResponseCode::invalid_header,
                         "disallowed regular expression '" + string(value) +
                             "': must not contain { or }");
            } else {
                _regex = new regex_t();
                bool ignore_case =
                    _relOp == RelationalOperator::matches_icase ||
                    _relOp == RelationalOperator::doesnt_match_icase;
                if (regcomp(_regex, search_space,
                            REG_EXTENDED | REG_NOSUB |
                                (ignore_case ? REG_ICASE : 0)) != 0) {
                    setError(
                        OutputBuffer::ResponseCode::invalid_header,
                        "invalid regular expression '" + string(value) + "'");
                    delete _regex;
                    _regex = nullptr;
                }
            }
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

CustomVarsFilter::~CustomVarsFilter() {
    if (_regex != nullptr) {
        regfree(_regex);
        delete _regex;
    }
}

bool CustomVarsFilter::accepts(void *data) {
    if (_column->type() == ColumnType::dict) {
        const char *act_string =
            _column->getVariable(data, _ref_varname.c_str());
        if (act_string == nullptr) {
            act_string = "";
        }
        switch (_relOp) {
            case RelationalOperator::equal:
                return act_string == _ref_string;
            case RelationalOperator::not_equal:
                return act_string != _ref_string;
            case RelationalOperator::matches:
            case RelationalOperator::matches_icase:
                return _regex != nullptr &&
                       regexec(_regex, act_string, 0, nullptr, 0) == 0;
            case RelationalOperator::doesnt_match:
            case RelationalOperator::doesnt_match_icase:
                return _regex != nullptr &&
                       regexec(_regex, act_string, 0, nullptr, 0) != 0;
            case RelationalOperator::equal_icase:
                return strcasecmp(_ref_string.c_str(), act_string) == 0;
            case RelationalOperator::not_equal_icase:
                return strcasecmp(_ref_string.c_str(), act_string) != 0;
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
    bool is_member = _column->contains(data, _ref_text.c_str());
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
            Informational()
                << "Sorry. Operator " << _relOp
                << " for custom variable list columns not implemented.";
            return false;
    }
    return false;  // unreachable
}

CustomVarsColumn *CustomVarsFilter::column() { return _column; }
