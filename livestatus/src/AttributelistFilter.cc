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

#include "AttributelistFilter.h"
#include <ostream>
#include "AttributelistColumn.h"
#include "Logger.h"

AttributelistFilter::AttributelistFilter(AttributelistColumn *column,
                                         RelationalOperator relOp,
                                         unsigned long ref)
    : _column(column), _relOp(relOp), _ref(ref) {}

/* The following operators are defined:

   modified_attributes = 6
   modified_attributes = notifications_enabled

   --> Exact match

   modified_attributes ~ 6
   modified_attributes ~ notifications_enabled

   --> Must contain at least those bits

   modified_attributes ~~ 6
   modified_attributes ~~ notifications_enabled

   --> Must contain at least one of those bits

   Also number comparisons
 */

AttributelistColumn *AttributelistFilter::column() { return _column; }

bool AttributelistFilter::accepts(void *row, contact * /* auth_user */,
                                  int /* timezone_offset */) {
    unsigned long act_value =
        static_cast<unsigned long>(_column->getValue(row, nullptr));
    switch (_relOp) {
        case RelationalOperator::equal:
            return act_value == _ref;
        case RelationalOperator::not_equal:
            return act_value != _ref;
        case RelationalOperator::matches:
            return (act_value & _ref) == _ref;
        case RelationalOperator::doesnt_match:
            return (act_value & _ref) != _ref;
        case RelationalOperator::matches_icase:
            return (act_value & _ref) != 0;
        case RelationalOperator::doesnt_match_icase:
            return (act_value & _ref) == 0;
        case RelationalOperator::less:
            return act_value < _ref;
        case RelationalOperator::greater_or_equal:
            return act_value >= _ref;
        case RelationalOperator::greater:
            return act_value > _ref;
        case RelationalOperator::less_or_equal:
            return act_value <= _ref;
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
            Informational(_logger)
                << "Sorry. Operator " << _relOp
                << " for attribute list columns not implemented.";
            return false;
    }
    return false;  // unreachable
}
