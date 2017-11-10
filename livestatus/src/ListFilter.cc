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

#include "ListFilter.h"
#include <algorithm>
#include <cstring>
#include <sstream>
#include <string>
#include "Filter.h"
#include "ListColumn.h"
#include "Logger.h"
#include "Row.h"

ListFilter::ListFilter(const ListColumn &column, RelationalOperator relOp,
                       std::string value)
    : _column(column), _relOp(relOp), _value(std::move(value)) {
    switch (_relOp) {
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            _regex.assign(_value,
                          (_relOp == RelationalOperator::matches_icase ||
                           _relOp == RelationalOperator::doesnt_match_icase)
                              ? std::regex::extended | std::regex::icase
                              : std::regex::extended);
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

bool ListFilter::accepts(Row row, const contact *auth_user,
                         std::chrono::seconds timezone_offset) const {
    switch (_relOp) {
        case RelationalOperator::equal:
            if (!_value.empty()) {
                Informational(_column.logger())
                    << "Sorry, equality for lists implemented only for emptiness";
                return false;
            }
            return !any(row, auth_user, timezone_offset,
                        [](const std::string &) { return true; });
        case RelationalOperator::not_equal:
            if (!_value.empty()) {
                Informational(_column.logger())
                    << "Sorry, inequality for lists implemented only for emptiness";
                return false;
            }
            return any(row, auth_user, timezone_offset,
                       [](const std::string &) { return true; });
        case RelationalOperator::matches:
        case RelationalOperator::matches_icase:
            return any(row, auth_user, timezone_offset,
                       [&](const std::string &elem) {
                           return regex_search(elem, _regex);
                       });
        case RelationalOperator::doesnt_match:
        case RelationalOperator::doesnt_match_icase:
            return !any(row, auth_user, timezone_offset,
                        [&](const std::string &elem) {
                            return regex_search(elem, _regex);
                        });
        case RelationalOperator::less:
            return !any(
                row, auth_user, timezone_offset,
                [&](const std::string &elem) { return _value == elem; });
        case RelationalOperator::greater_or_equal:
            return any(row, auth_user, timezone_offset,
                       [&](const std::string &elem) { return _value == elem; });
        case RelationalOperator::greater:
            return !any(
                row, auth_user, timezone_offset, [&](const std::string &elem) {
                    return strcasecmp(_value.c_str(), elem.c_str()) == 0;
                });
        case RelationalOperator::less_or_equal:
            return any(row, auth_user, timezone_offset,
                       [&](const std::string &elem) {
                           return strcasecmp(_value.c_str(), elem.c_str()) == 0;
                       });
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
            Informational(_column.logger())
                << "Sorry. Operator " << _relOp
                << " for list columns not implemented.";
            return false;
    }
    return false;  // unreachable
}

const std::string *ListFilter::valueForIndexing(
    const std::string &column_name) const {
    switch (_relOp) {
        case RelationalOperator::greater_or_equal:
            return column_name == columnName() ? &_value : nullptr;
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
        case RelationalOperator::less:
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
            return nullptr;
    }
    return nullptr;  // unreachable
}

std::unique_ptr<Filter> ListFilter::copy() const {
    return std::make_unique<ListFilter>(*this);
}

std::unique_ptr<Filter> ListFilter::negate() const {
    return std::make_unique<ListFilter>(
        _column, negateRelationalOperator(_relOp), _value);
}

std::string ListFilter::columnName() const { return _column.name(); }
