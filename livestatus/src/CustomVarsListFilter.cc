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

#include "CustomVarsListFilter.h"
#include <algorithm>
#include <sstream>
#include "CustomVarsColumn.h"
#include "Logger.h"
#include "Row.h"

using std::move;
using std::string;

CustomVarsListFilter::CustomVarsListFilter(const CustomVarsColumn &column,
                                           RelationalOperator relOp,
                                           string value)
    : _column(column), _relOp(relOp), _ref_text(move(value)) {}

bool CustomVarsListFilter::accepts(Row row, contact * /* auth_user */,
                                   int /* timezone_offset */) const {
    bool is_member = _column.contains(row, _ref_text);
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
            Informational(_column.logger())
                << "Sorry. Operator " << _relOp
                << " for custom variable list columns not implemented.";
            return false;
    }
    return false;  // unreachable
}

string CustomVarsListFilter::columnName() const { return _column.name(); }
