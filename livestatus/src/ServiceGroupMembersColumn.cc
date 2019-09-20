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

#include "ServiceGroupMembersColumn.h"
#include <algorithm>
#include <iterator>
#include <ostream>
#include "Filter.h"
#include "ListFilter.h"
#include "Logger.h"
#include "Renderer.h"
#include "Row.h"

#ifdef CMC
#include <unordered_set>
#include "Host.h"
#include "LogEntry.h"
#include "Service.h"
#include "State.h"
#else
#include "auth.h"
#endif

void ServiceGroupMembersColumn::output(
    Row row, RowRenderer &r, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    ListRenderer l(r);
    for (const auto &member : getMembers(row, auth_user)) {
        SublistRenderer s(l);
        s.output(member.host_name);
        s.output(member.description);
        if (_show_state) {
            s.output(static_cast<int>(member.current_state));
            s.output(static_cast<bool>(member.has_been_checked));
        }
    }
}

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

std::unique_ptr<Filter> ServiceGroupMembersColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<ListFilter>(kind, *this, relOp,
                                        checkValue(logger(), relOp, value));
}

std::vector<std::string> ServiceGroupMembersColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    auto members = getMembers(row, auth_user);
    std::vector<std::string> specnames;
    std::transform(members.begin(), members.end(),
                   std::back_inserter(specnames), [](const auto &member) {
                       return member.host_name + separator() +
                              member.description;
                   });
    return specnames;
}

std::vector<ServiceGroupMembersColumn::Member>
ServiceGroupMembersColumn::getMembers(Row row, const contact *auth_user) const {
    std::vector<Member> members;
#ifdef CMC
    (void)_mc;  // HACK
    if (auto p = columnData<Host::services_t>(row)) {
        for (auto &svc : *p) {
            if (auth_user == nullptr || svc->hasContact(auth_user)) {
                members.emplace_back(
                    svc->host()->name(), svc->name(),
                    static_cast<ServiceState>(svc->state()->_current_state),
                    svc->state()->_has_been_checked);
            }
        }
    }
#else
    if (auto p = columnData<servicesmember *>(row)) {
        for (servicesmember *mem = *p; mem != nullptr; mem = mem->next) {
            service *svc = mem->service_ptr;
            if (auth_user == nullptr ||
                is_authorized_for(_mc, auth_user, svc->host_ptr, svc)) {
                members.emplace_back(
                    svc->host_name, svc->description,
                    static_cast<ServiceState>(svc->current_state),
                    svc->has_been_checked != 0);
            }
        }
    }
#endif
    return members;
}
