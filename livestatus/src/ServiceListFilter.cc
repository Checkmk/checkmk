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

#include "ServiceListFilter.h"
#include <ostream>
#include "Logger.h"
#include "Row.h"
#include "ServiceListColumn.h"

#ifdef CMC
#include <memory>
#include "Host.h"
#include "Service.h"
#include "cmc.h"
#else
#include "nagios.h"
#endif

namespace {
constexpr char hostservice_separator = '|';
}  // namespace

ServiceListFilter::ServiceListFilter(const ServiceListColumn &column,
                                     bool hostname_required,
                                     RelationalOperator relOp,
                                     const std::string &value)
    : _column(column), _hostname_required(hostname_required), _relOp(relOp) {
    if ((_relOp == RelationalOperator::equal ||
         _relOp == RelationalOperator::not_equal) &&
        value.empty()) {
        return;  // test for emptiness is allowed
    }

    // ref_value must be of the form
    //    hostname hostservice_separator service_description
    auto pos = value.find(hostservice_separator);
    if (pos == std::string::npos) {
        if (_hostname_required) {
            Informational(_column.logger())
                << "Invalid reference value for service "
                   "list membership. Must be 'hostname"
                << std::string(1, hostservice_separator) << "servicename'";
        } else {
            _ref_service = value;
        }
    } else {
        _ref_host = value.substr(0, pos);
        _ref_service = value.substr(pos + 1);
    }
}

namespace {
bool isEmpty(ServiceListColumn::service_list servicelist) {
#ifdef CMC
    return servicelist->empty();
#else
    return servicelist == nullptr;
#endif
}

bool contains(ServiceListColumn::service_list servicelist,
              const std::string &ref_host, const std::string &ref_service,
              bool hostname_required) {
#ifdef CMC
    for (const auto &service : *servicelist) {
        if ((!hostname_required || service->host()->name() == ref_host) &&
            service->name() == ref_service) {
            return true;
        }
    }
    return false;
#else
    for (; servicelist != nullptr; servicelist = servicelist->next) {
        service *svc = servicelist->service_ptr;
        if ((!hostname_required || svc->host_name == ref_host) &&
            svc->description == ref_service) {
            return true;
        }
    }
    return false;
#endif
}
}  // namespace

bool ServiceListFilter::accepts(
    Row row, const contact * /* auth_user */,
    std::chrono::seconds /* timezone_offset */) const {
    auto servicelist = _column.getMembers(row);
    switch (_relOp) {
        case RelationalOperator::equal:
            if (!_ref_host.empty()) {
                Informational(_column.logger())
                    << "Sorry, equality for service lists implemented only for emptiness";
                return false;
            }
            return isEmpty(servicelist);
        case RelationalOperator::not_equal:
            if (!_ref_host.empty()) {
                Informational(_column.logger())
                    << "Sorry, inequality for service lists implemented only for emptiness";
                return false;
            }
            return !isEmpty(servicelist);
        case RelationalOperator::less:
            return !contains(servicelist, _ref_host, _ref_service,
                             _hostname_required);
        case RelationalOperator::greater_or_equal:
            return contains(servicelist, _ref_host, _ref_service,
                            _hostname_required);
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
                << " for service lists not implemented.";
            return false;
    }
    return false;  // unreachable
}

std::string ServiceListFilter::columnName() const { return _column.name(); }
