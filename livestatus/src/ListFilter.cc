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
#include <ostream>
#include <vector>
#include "ListColumn.h"
#include "Logger.h"
#include "Row.h"

ListFilter::ListFilter(const ListColumn &column, RelationalOperator relOp,
                       std::string element)
    : _column(column), _relOp(relOp), _element(std::move(element)) {}

bool ListFilter::accepts(Row row, const contact *auth_user,
                         std::chrono::seconds /* timezone_offset */) const {
    switch (_relOp) {
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
            if (!_element.empty()) {
                Informational(_column.logger())
                    << "Sorry, equality for lists implemented only for emptyness";
            }
            return _column.getValue(row, auth_user).empty() ==
                   (_relOp == RelationalOperator::equal);
        case RelationalOperator::less:
        case RelationalOperator::greater_or_equal: {
            auto val = _column.getValue(row, auth_user);
            return (std::find(val.begin(), val.end(), _element) == val.end()) ==
                   (_relOp == RelationalOperator::less);
        }
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
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
            return column_name == columnName() ? &_element : nullptr;
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

std::string ListFilter::columnName() const { return _column.name(); }
