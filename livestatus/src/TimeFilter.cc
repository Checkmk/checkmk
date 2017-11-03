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

#include "TimeFilter.h"
#include <cstdlib>
#include <ostream>
#include "Logger.h"
#include "Row.h"
#include "TimeColumn.h"

TimeFilter::TimeFilter(const TimeColumn &column, RelationalOperator relOp,
                       const std::string &value)
    : _column(column), _relOp(relOp), _ref_value(atoi(value.c_str())) {}

std::string TimeFilter::columnName() const { return _column.name(); }

int32_t TimeFilter::convertRefValue(
    std::chrono::seconds timezone_offset) const {
    return _ref_value - timezone_offset.count();
}

bool TimeFilter::accepts(Row row, const contact *auth_user,
                         std::chrono::seconds timezone_offset) const {
    // NOTE: TimeColumn::getValue() call site
    int32_t act_value =
        std::chrono::system_clock::to_time_t(_column.getValue(row, auth_user));
    int32_t ref_value = convertRefValue(timezone_offset);
    switch (_relOp) {
        case RelationalOperator::equal:
            return act_value == ref_value;
        case RelationalOperator::not_equal:
            return act_value != ref_value;
        case RelationalOperator::matches:  // superset
            return (act_value & ref_value) == ref_value;
        case RelationalOperator::doesnt_match:  // not superset
            return (act_value & ref_value) != ref_value;
        case RelationalOperator::equal_icase:  // subset
            return (act_value & ref_value) == act_value;
        case RelationalOperator::not_equal_icase:  // not subset
            return (act_value & ref_value) != act_value;
        case RelationalOperator::matches_icase:  // contains any
            return (act_value & ref_value) != 0;
        case RelationalOperator::doesnt_match_icase:  // contains none of
            return (act_value & ref_value) == 0;
        case RelationalOperator::less:
            return act_value < ref_value;
        case RelationalOperator::greater_or_equal:
            return act_value >= ref_value;
        case RelationalOperator::greater:
            return act_value > ref_value;
        case RelationalOperator::less_or_equal:
            return act_value <= ref_value;
    }
    return false;  // unreachable
}

void TimeFilter::findIntLimits(const std::string &column_name, int *lower,
                               int *upper,
                               std::chrono::seconds timezone_offset) const {
    if (column_name != columnName()) {
        return;  // wrong column
    }
    if (*lower >= *upper) {
        return;  // already empty interval
    }

    int32_t ref_value = convertRefValue(timezone_offset);

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
            Emergency(_column.logger())
                << "Invalid relational operator " << _relOp
                << " in TimeFilter::findIntLimits";
            return;
    }
}

bool TimeFilter::optimizeBitmask(const std::string &column_name, uint32_t *mask,
                                 std::chrono::seconds timezone_offset) const {
    int32_t ref_value = convertRefValue(timezone_offset);

    if (column_name != columnName()) {
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
            Emergency(_column.logger())
                << "Invalid relational operator " << _relOp
                << " in TimeFilter::optimizeBitmask";
            return false;
    }
    return false;  // unreachable
}
