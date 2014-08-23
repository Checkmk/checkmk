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

#include <stdlib.h>
#include <string.h>
#include "IntColumnFilter.h"
#include "IntColumn.h"
#include "logger.h"
#include "opids.h"

    IntColumnFilter::IntColumnFilter(IntColumn *column, int opid, char *value)
    : _column(column)
    , _opid(abs(opid))
    , _negate(opid < 0)
      , _ref_string(value)
{
}

// overridden by TimeColumnFilter in order to apply timezone
// offset from Localtime: header
int32_t IntColumnFilter::convertRefValue()
{
    return atoi(_ref_string.c_str());
}

bool IntColumnFilter::accepts(void *data)
{
    bool pass = true;
    int32_t act_value = _column->getValue(data, _query);
    int32_t ref_value = convertRefValue();
    switch (_opid) {
        case OP_EQUAL:
            pass = act_value == ref_value; break;
        case OP_GREATER:
            pass = act_value > ref_value; break;
        case OP_LESS:
            pass = act_value < ref_value; break;
        default:
            logger(LG_INFO, "Sorry. Operator %s for integers not implemented.", op_names_plus_8[_opid]);
            break;
    }
    return pass != _negate;
}

void IntColumnFilter::findIntLimits(const char *columnname, int *lower, int *upper)
{
    if (strcmp(columnname, _column->name())) {
        return; // wrong column
    }
    if (*lower >= *upper) {
        return; // already empty interval
    }

    int32_t ref_value = convertRefValue(); // TimeColumnFilter applies timezone offset here

    /* [lower, upper[ is some interval. This filter might restrict
       that interval to a smaller interval.
     */
    int opref = _opid * (_negate != false ? -1 : 1);
    switch (opref) {
        case OP_EQUAL:
            if (ref_value >= *lower && ref_value < *upper) {
                *lower = ref_value;
                *upper = ref_value + 1;
            }
            else
                *lower = *upper;
            return;

        case -OP_EQUAL:
            if (ref_value == *lower)
                *lower = *lower + 1;
            else if (ref_value == *upper - 1)
                *upper = *upper - 1;
            return;

        case OP_GREATER:
            if (ref_value >= *lower) {
                *lower = ref_value + 1;
            }

            return;

        case OP_LESS:
            if (ref_value < *upper)
                *upper = ref_value;
            return;

        case -OP_GREATER: // LESS OR EQUAL
            if (ref_value < *upper - 1)
                *upper = ref_value + 1;
            return;

        case -OP_LESS: // GREATER OR EQUAL
            if (ref_value > *lower)
                *lower = ref_value;
            return;
    }
}


bool IntColumnFilter::optimizeBitmask(const char *columnname, uint32_t *mask)
{
    int32_t ref_value = convertRefValue();

    if (strcmp(columnname, _column->name())) {
        return false; // wrong column
    }

    if (ref_value < 0 || ref_value > 31)
        return true; // not optimizable by 32bit bit mask

    // Our task is to remove those bits from mask that are deselected
    // by the filter.
    uint32_t bit = 1 << ref_value;

    int opref = _opid * (_negate != false ? -1 : 1);
    switch (opref) {
        case OP_EQUAL:
            *mask &= bit; // bit must be set
            return true;

        case -OP_EQUAL:
            *mask &= ~bit; // bit must not be set
            return true;

        case -OP_LESS: // >=
            bit >>= 1;
        case OP_GREATER:
            while (bit) {
                *mask &= ~bit;
                bit >>= 1;
            }
            return true;

        case -OP_GREATER: // <=
            if (ref_value == 31)
                return true;
            bit <<= 1;
        case OP_LESS:
            while (true) {
                *mask &= ~bit;
                if (bit == 0x80000000)
                    return true;
                bit <<= 1;
            }
            return true;
    }
    return false; // should not be reached
}

