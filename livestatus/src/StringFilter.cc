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
#include <string.h>
#include <stdexcept>
#include "StringColumn.h"
#include "opids.h"

using std::runtime_error;
using std::string;

StringFilter::StringFilter(Query *query, StringColumn *column,
                           RelationalOperator relOp, const string &value)
    : ColumnFilter(query)
    , _column(column)
    , _relOp(relOp)
    , _ref_string(value)
    , _regex(nullptr) {
    switch (_relOp) {
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            if (strchr(value.c_str(), '{') != nullptr ||
                strchr(value.c_str(), '}') != nullptr) {
                throw runtime_error("disallowed regular expression '" + value +
                                    "': must not contain { or }");
            } else {
                _regex = new regex_t();
                bool ignore_case =
                    _relOp == RelationalOperator::matches_icase ||
                    _relOp == RelationalOperator::doesnt_match_icase;
                if (regcomp(_regex, value.c_str(),
                            REG_EXTENDED | REG_NOSUB |
                                (ignore_case ? REG_ICASE : 0)) != 0) {
                    delete _regex;
                    throw runtime_error("invalid regular expression '" + value +
                                        "'");
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

StringFilter::~StringFilter() {
    if (_regex != nullptr) {
        regfree(_regex);
        delete _regex;
    }
}

bool StringFilter::accepts(void *data) {
    string act_string = _column->getValue(data);
    switch (_relOp) {
        case RelationalOperator::equal:
            return act_string == _ref_string;
        case RelationalOperator::not_equal:
            return act_string != _ref_string;
        case RelationalOperator::matches:
        case RelationalOperator::matches_icase:
            return _regex != nullptr &&
                   regexec(_regex, act_string.c_str(), 0, nullptr, 0) == 0;
        case RelationalOperator::doesnt_match:
        case RelationalOperator::doesnt_match_icase:
            return _regex != nullptr &&
                   regexec(_regex, act_string.c_str(), 0, nullptr, 0) != 0;
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
            return column_name == _column->name() ? &_ref_string : nullptr;
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

StringColumn *StringFilter::column() { return _column; }
