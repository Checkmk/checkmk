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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "AttributelistFilter.h"
#include "AttributelistColumn.h"
#include "opids.h"
#include "logger.h"


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


bool AttributelistFilter::accepts(void *data)
{
    unsigned long act_value = _column->getValue(data);
    bool pass = true;
    switch (_opid) {
        case OP_EQUAL:
            pass = act_value == _ref; break;
        case OP_GREATER:
            pass = act_value > _ref; break;
        case OP_LESS:
            pass = act_value < _ref; break;
        case OP_REGEX:
            pass = (act_value & _ref) == _ref; break;
        case OP_REGEX_ICASE:
            pass = (act_value & _ref) != 0; break;
        default:
            logger(LG_INFO, "Sorry. Operator %s not implemented for attribute lists", op_names_plus_8[_opid]);
    }
    return pass != _negate;
}

