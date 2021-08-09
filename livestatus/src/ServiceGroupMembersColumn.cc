// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceGroupMembersColumn.h"

#include <algorithm>
#include <iterator>

#include "ListFilter.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "Renderer.h"
#include "Row.h"
#include "auth.h"

#ifdef CMC
#include <unordered_set>

#include "Host.h"
#include "LogEntry.h"
#include "ObjectGroup.h"
#include "Service.h"
#include "State.h"
#endif

void ServiceGroupMembersRenderer::operator()(Row row, RowRenderer &r,
                                             const contact *auth_user) const {
    ListRenderer l(r);
    for (const auto &entry : f_(row, auth_user)) {
        switch (verbosity_) {
            case verbosity::none: {
                SublistRenderer s(l);
                s.output(entry.host_name);
                s.output(entry.description);
                break;
            }
            case verbosity::full: {
                SublistRenderer s(l);
                s.output(entry.host_name);
                s.output(entry.description);
                s.output(static_cast<int>(entry.current_state));
                s.output(static_cast<bool>(entry.has_been_checked));
                break;
            }
        }
    }
}

void ServiceGroupMembersColumn::output(
    Row row, RowRenderer &r, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    renderer_(row, r, auth_user);
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
    return std::make_unique<ListFilter>(
        kind, name(),
        // `timezone_offset` is unused
        [this](Row row, const contact *auth_user,
               std::chrono::seconds timezone_offset) {
            return getValue(row, auth_user, timezone_offset);
        },
        relOp, checkValue(logger(), relOp, value), logger());
}

/// \sa Apart from the lambda, the code is the same in
///    * CommentColumn::getValue()
///    * DowntimeColumn::getValue()
///    * ServiceGroupMembersColumn::getValue()
///    * ServiceListColumn::getValue()
std::vector<std::string> ServiceGroupMembersColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    auto entries = getEntries(row, auth_user);
    std::vector<std::string> values;
    std::transform(entries.begin(), entries.end(), std::back_inserter(values),
                   [](const auto &entry) {
                       return entry.host_name + separator() + entry.description;
                   });
    return values;
}

std::vector<ServiceGroupMembersColumn::Entry>
ServiceGroupMembersColumn::getEntries(Row row, const contact *auth_user) const {
    std::vector<Entry> entries;
#ifdef CMC
    if (const auto *p = columnData<ObjectGroup<Service>::values_type>(row)) {
        for (const auto *svc : *p) {
            if (is_authorized_for_svc(mc_->serviceAuthorization(), auth_user,
                                      svc)) {
                entries.emplace_back(
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
            if (is_authorized_for_svc(mc_->serviceAuthorization(), auth_user,
                                      svc)) {
                entries.emplace_back(
                    svc->host_name, svc->description,
                    static_cast<ServiceState>(svc->current_state),
                    svc->has_been_checked != 0);
            }
        }
    }
#endif
    return entries;
}
