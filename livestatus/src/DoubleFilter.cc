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

#include "DoubleFilter.h"
#include <cstdlib>
#include <ostream>
#include "DoubleColumn.h"
#include "Logger.h"
#include "Row.h"

using std::string;

DoubleFilter::DoubleFilter(const DoubleColumn &column, RelationalOperator relOp,
                           const string &value)
    : _column(column), _relOp(relOp), _ref_value(atof(value.c_str())) {}

bool DoubleFilter::accepts(Row row, contact * /* auth_user */,
                           int /* timezone_offset */) const {
    double act_value = _column.getValue(row);
    switch (_relOp) {
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
                << "Sorry. Operator " << _relOp
                << " for float columns not implemented.";
            return false;
    }
    return false;  // unreachable
}

string DoubleFilter::columnName() const { return _column.name(); }
