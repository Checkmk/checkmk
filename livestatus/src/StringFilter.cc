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
#include <cstring>
#include <sstream>
#include "Row.h"
#include "StringColumn.h"

using std::move;
using std::regex;
using std::regex_search;
using std::string;

StringFilter::StringFilter(const StringColumn &column, RelationalOperator relOp,
                           string value)
    : _column(column), _relOp(relOp), _ref_string(move(value)) {
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

bool StringFilter::accepts(Row row, const contact * /* auth_user */,
                           int /* timezone_offset */) const {
    string act_string = _column.getValue(row);
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
    return false;  // unreachable
}

const string *StringFilter::valueForIndexing(const string &column_name) const {
    switch (_relOp) {
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
            // TODO(sp) The cast looks very dubious, but the whole void* story
            // is quite dangerous...
            return column_name == columnName() ? &_ref_string : nullptr;
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

string StringFilter::columnName() const { return _column.name(); }
