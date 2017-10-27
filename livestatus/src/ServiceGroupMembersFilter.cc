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

#include "ServiceGroupMembersFilter.h"
#include <ostream>
#include "Logger.h"
#include "ServiceGroupMembersColumn.h"

namespace {
// value must be of the form
//    hostname hostservice_separator service_description
std::string checkValue(Logger *logger, RelationalOperator relOp,
                       const std::string &value) {
    auto pos = value.find(ServiceGroupMembersColumn::separator());
    bool equality = relOp == RelationalOperator::equal ||
                    relOp == RelationalOperator::not_equal;
    if (pos == std::string::npos && !(equality && value.empty())) {
        Informational(logger)
            << "Invalid reference value for service list membership. Must be 'hostname"
            << ServiceGroupMembersColumn::separator() << "servicename'";
    }
    return value;
}
}  // namespace

ServiceGroupMembersFilter::ServiceGroupMembersFilter(
    const ServiceGroupMembersColumn &column, RelationalOperator relOp,
    const std::string &value)
    : ListFilter(column, relOp, checkValue(column.logger(), relOp, value)) {}
