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

#include "IntColumnFilter.h"
#include <stdlib.h>
#include <ostream>
#include <utility>
#include "IntColumn.h"
#include "Logger.h"
#include "opids.h"

using std::move;
using std::string;

IntColumnFilter::IntColumnFilter(IntColumn *column, RelationalOperator relOp,
                                 string value)
    : _column(column), _relOp(relOp), _ref_string(move(value)) {}

// overridden by TimeColumnFilter in order to apply timezone
// offset from Localtime: header
int32_t IntColumnFilter::convertRefValue() { return atoi(_ref_string.c_str()); }

bool IntColumnFilter::accepts(void *data) {
    int32_t act_value = _column->getValue(data, _query);
    int32_t ref_value = convertRefValue();
    switch (_relOp) {
        case RelationalOperator::equal:
            return act_value == ref_value;
        case RelationalOperator::not_equal:
            return act_value != ref_value;
        case RelationalOperator::less:
            return act_value < ref_value;
        case RelationalOperator::greater_or_equal:
            return act_value >= ref_value;
        case RelationalOperator::greater:
            return act_value > ref_value;
        case RelationalOperator::less_or_equal:
            return act_value <= ref_value;
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            Informational() << "Sorry. Operator " << _relOp
                            << " for integer columns not implemented.";
            return false;
    }
    return false;  // unreachable
}

void IntColumnFilter::findIntLimits(const string &column_name, int *lower,
                                    int *upper) {
    if (column_name != _column->name()) {
        return;  // wrong column
    }
    if (*lower >= *upper) {
        return;  // already empty interval
    }

    // TimeColumnFilter applies timezone offset here
    int32_t ref_value = convertRefValue();

    /* [lower, upper[ is some interval. This filter might restrict that interval
       to a smaller interval.
     */
    switch (_relOp) {
        case RelationalOperator::equal:
            if (ref_value >= *lower && ref_value < *upper) {
                *lower = ref_value;
                *upper = ref_value + 1;
            } else {
                *lower = *upper;
            }
            return;
        case RelationalOperator::not_equal:
            if (ref_value == *lower) {
                *lower = *lower + 1;
            } else if (ref_value == *upper - 1) {
                *upper = *upper - 1;
            }
            return;
        case RelationalOperator::less:
            if (ref_value < *upper) {
                *upper = ref_value;
            }
            return;
        case RelationalOperator::greater_or_equal:
            if (ref_value > *lower) {
                *lower = ref_value;
            }
            return;
        case RelationalOperator::greater:
            if (ref_value >= *lower) {
                *lower = ref_value + 1;
            }
            return;
        case RelationalOperator::less_or_equal:
            if (ref_value < *upper - 1) {
                *upper = ref_value + 1;
            }
            return;
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            Emergency() << "Invalid relational operator " << _relOp
                        << " in IntColumnFilter::findIntLimits";
            return;
    }
}

bool IntColumnFilter::optimizeBitmask(const string &column_name, uint32_t *mask) {
    int32_t ref_value = convertRefValue();

    if (column_name != _column->name()) {
        return false;  // wrong column
    }

    if (ref_value < 0 || ref_value > 31) {
        return true;  // not optimizable by 32bit bit mask
    }

    // Our task is to remove those bits from mask that are deselected by the
    // filter.
    uint32_t bit = 1 << ref_value;

    switch (_relOp) {
        case RelationalOperator::equal:
            *mask &= bit;  // bit must be set
            return true;
        case RelationalOperator::not_equal:
            *mask &= ~bit;  // bit must not be set
            return true;
        case RelationalOperator::greater_or_equal:
            bit >>= 1;
        // fallthrough
        case RelationalOperator::greater:
            while (bit != 0u) {
                *mask &= ~bit;
                bit >>= 1;
            }
            return true;
        case RelationalOperator::less_or_equal:
            if (ref_value == 31) {
                return true;
            }
            bit <<= 1;
        // fallthrough
        case RelationalOperator::less:
            while (true) {
                *mask &= ~bit;
                if (bit == 0x80000000) {
                    return true;
                }
                bit <<= 1;
            }
            return true;
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            Emergency() << "Invalid relational operator " << _relOp
                        << " in IntColumnFilter::optimizeBitmask";
            return false;
    }
    return false;  // unreachable
}
