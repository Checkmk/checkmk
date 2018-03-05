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

#include "Filter.h"
#include <ostream>

LogicalOperator dual(LogicalOperator op) {
    switch (op) {
        case LogicalOperator::and_:
            return LogicalOperator::or_;
        case LogicalOperator::or_:
            return LogicalOperator::and_;
        case LogicalOperator::stats_and:
            return LogicalOperator::stats_or;
        case LogicalOperator::stats_or:
            return LogicalOperator::stats_and;
        case LogicalOperator::wait_condition_and:
            return LogicalOperator::wait_condition_or;
        case LogicalOperator::wait_condition_or:
            return LogicalOperator::wait_condition_and;
    }
    return LogicalOperator::and_;  // unreachable, make the compiler happy
}

std::ostream &operator<<(std::ostream &os, const LogicalOperator &op) {
    switch (op) {
        case LogicalOperator::and_:
            return os << "And";
        case LogicalOperator::or_:
            return os << "Or";
        case LogicalOperator::stats_and:
            return os << "StatsAnd";
        case LogicalOperator::stats_or:
            return os << "StatsOr";
        case LogicalOperator::wait_condition_and:
            return os << "WaitConditionAnd";
        case LogicalOperator::wait_condition_or:
            return os << "WaitConditionOr";
    }
    return os;  // unreachable, make the compiler happy
}

Filter::~Filter() = default;

const std::string *Filter::stringValueRestrictionFor(
    const std::string & /* column_name */) const {
    return nullptr;
}

void Filter::findIntLimits(const std::string & /* column_name */,
                           int * /* lower */, int * /* upper */,
                           std::chrono::seconds /* timezone_offset */) const {}

bool Filter::optimizeBitmask(const std::string & /* column_name */,
                             uint32_t * /* mask */,
                             std::chrono::seconds /* timezone_offset */) const {
    return false;
}
