// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceListColumn.h"

#include <algorithm>
#include <iterator>

#include "MonitoringCore.h"
#include "Renderer.h"
#include "Row.h"
#include "auth.h"

#ifdef CMC
#include <memory>
#include <unordered_set>

#include "Host.h"
#include "LogEntry.h"
#include "Service.h"
#include "State.h"
#include "Timeperiod.h"
#else
#include <unordered_map>

#include "TimeperiodsCache.h"
#endif

void ServiceListRenderer::operator()(Row row, RowRenderer &r,
                                     const contact *auth_user) const {
    ListRenderer l(r);
    for (const auto &entry : f_(row, auth_user)) {
        switch (verbosity_) {
            case verbosity::none:
                l.output(std::string(entry.description));
                break;
            case verbosity::low: {
                SublistRenderer s(l);
                s.output(entry.description);
                s.output(static_cast<int>(entry.current_state));
                s.output(static_cast<int>(entry.has_been_checked));
                break;
            }
            case verbosity::medium: {
                SublistRenderer s(l);
                s.output(entry.description);
                s.output(static_cast<int>(entry.current_state));
                s.output(static_cast<int>(entry.has_been_checked));
                s.output(entry.plugin_output);
                break;
            }
            case verbosity::full: {
                SublistRenderer s(l);
                s.output(entry.description);
                s.output(static_cast<int>(entry.current_state));
                s.output(static_cast<int>(entry.has_been_checked));
                s.output(entry.plugin_output);
                s.output(static_cast<int>(entry.last_hard_state));
                s.output(entry.current_attempt);
                s.output(entry.max_check_attempts);
                s.output(entry.scheduled_downtime_depth);
                s.output(static_cast<int>(entry.acknowledged));
                s.output(static_cast<int>(entry.service_period_active));
                break;
            }
        }
    }
}

void ServiceListColumn::output(Row row, RowRenderer &r,
                               const contact *auth_user,
                               std::chrono::seconds /*timezone_offset*/) const {
    renderer_(row, r, auth_user);
}

/// \sa Apart from the lambda, the code is the same in
///    * CommentColumn::getValue()
///    * DowntimeColumn::getValue()
///    * ServiceGroupMembersColumn::getValue()
///    * ServiceListColumn::getValue()
std::vector<std::string> ServiceListColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    auto entries = getEntries(row, auth_user);
    std::vector<std::string> values;
    std::transform(entries.begin(), entries.end(), std::back_inserter(values),
                   [](const auto &entry) { return entry.description; });
    return values;
}

#ifndef CMC
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern TimeperiodsCache *g_timeperiods_cache;

namespace {
bool inCustomTimeperiod(MonitoringCore *mc, service *svc) {
    auto attrs = mc->customAttributes(&svc->custom_variables,
                                      AttributeKind::custom_variables);
    auto it = attrs.find("SERVICE_PERIOD");
    if (it != attrs.end()) {
        return g_timeperiods_cache->inTimeperiod(it->second);
    }
    return true;  // assume 24X7
}
}  // namespace
#endif

std::vector<ServiceListColumn::Entry> ServiceListColumn::getEntries(
    Row row, const contact *auth_user) const {
    std::vector<Entry> entries;
#ifdef CMC
    if (const auto *mem = columnData<Host::services_t>(row)) {
        for (const auto &svc : *mem) {
            if (is_authorized_for_svc(mc_->serviceAuthorization(), auth_user,
                                      svc.get())) {
                entries.emplace_back(
                    svc->name(),
                    static_cast<ServiceState>(svc->state()->_current_state),
                    svc->state()->_has_been_checked,
                    svc->state()->_plugin_output,
                    static_cast<ServiceState>(svc->state()->_last_hard_state),
                    svc->state()->_current_attempt, svc->_max_check_attempts,
                    svc->state()->_scheduled_downtime_depth,
                    svc->acknowledged(), svc->_service_period->isActive());
            }
        }
    }
#else
    if (const auto *const p = columnData<servicesmember *>(row)) {
        for (servicesmember *mem = *p; mem != nullptr; mem = mem->next) {
            service *svc = mem->service_ptr;
            if (is_authorized_for_svc(mc_->serviceAuthorization(), auth_user,
                                      svc)) {
                entries.emplace_back(
                    svc->description,
                    static_cast<ServiceState>(svc->current_state),
                    svc->has_been_checked != 0,
                    svc->plugin_output == nullptr
                        ? ""
                        : std::string(svc->plugin_output),
                    static_cast<ServiceState>(svc->last_hard_state),
                    svc->current_attempt, svc->max_attempts,
                    svc->scheduled_downtime_depth,
                    svc->problem_has_been_acknowledged != 0,
                    inCustomTimeperiod(mc_, svc));
            }
        }
    }
#endif
    return entries;
}
