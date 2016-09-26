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

// IWYU pragma: no_include <ext/alloc_traits.h>
#include "ServicelistFilter.h"
#include <cstring>
#include <ostream>
#include "Logger.h"
#include "ServicelistColumn.h"
#include "nagios.h"

using std::string;

#define HOSTSERVICE_SEPARATOR '|'

ServicelistFilter::ServicelistFilter(ServicelistColumn *column,
                                     RelationalOperator relOp,
                                     const string &value)
    : _column(column), _relOp(relOp) {
    if ((_relOp == RelationalOperator::equal ||
         _relOp == RelationalOperator::not_equal) &&
        value.empty()) {
        return;  // test for emptiness is allowed
    }

    // ref_value must be of from hostname HOSTSERVICE_SEPARATOR
    // service_description
    const char *sep = index(value.c_str(), HOSTSERVICE_SEPARATOR);
    if (sep == nullptr) {
        Informational() << "Invalid reference value for service list "
                           "membership. Must be 'hostname"
                        << string(1, HOSTSERVICE_SEPARATOR) << "servicename'";
        _ref_host = "";
        _ref_service = "";
    } else {
        _ref_host = string(&value[0], sep - &value[0]);
        _ref_service = sep + 1;
    }
}

bool ServicelistFilter::accepts(void *row, contact * /* auth_user */,
                                int /* timezone_offset */) {
    // data points to a primary data object. We need to extract
    // a pointer to a service list
    servicesmember *mem = _column->getMembers(row);

    // test for empty list
    if (_ref_host.empty()) {
        if (_relOp == RelationalOperator::equal) {
            return mem == nullptr;
        }
        if (_relOp == RelationalOperator::not_equal) {
            return mem != nullptr;
        }
    }

    bool is_member = false;
    for (; mem != nullptr; mem = mem->next) {
        service *svc = mem->service_ptr;
        if (svc->host_name == _ref_host && svc->description == _ref_service) {
            is_member = true;
            break;
        }
    }

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
            Informational() << "Sorry. Operator " << _relOp
                            << " for service lists not implemented.";
            return false;
    }
    return false;  // unreachable
}

ServicelistColumn *ServicelistFilter::column() { return _column; }
