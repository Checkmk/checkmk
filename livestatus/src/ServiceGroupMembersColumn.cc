// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceGroupMembersColumn.h"

#include <algorithm>
#include <iterator>

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
    if (const auto *p = columnData<Host::services_t>(row)) {
        for (const auto &svc : *p) {
            if (auth_user == nullptr || svc->hasContact(auth_user)) {
                members.emplace_back(
                    svc->host()->name(), svc->name(),
                    static_cast<ServiceState>(svc->state()->_current_state),
                    svc->state()->_has_been_checked);
            }
        }
    }
#else
    if (const auto *p = columnData<servicesmember *>(row)) {
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
