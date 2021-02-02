// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceListColumn.h"

#include <algorithm>
#include <iterator>

#include "Renderer.h"
#include "Row.h"

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

#include "MonitoringCore.h"
#include "TimeperiodsCache.h"
#include "auth.h"
#endif

void ServiceListColumn::output(Row row, RowRenderer &r,
                               const contact *auth_user,
                               std::chrono::seconds /*timezone_offset*/) const {
    ListRenderer l(r);
    for (const auto &entry : getEntries(row, auth_user)) {
        if (_info_depth == 0) {
            l.output(std::string(entry.description));
        } else {
            SublistRenderer s(l);
            s.output(entry.description);
            if (_info_depth >= 1) {
                s.output(static_cast<int>(entry.current_state));
                s.output(static_cast<int>(entry.has_been_checked));
            }
            if (_info_depth >= 2) {
                s.output(entry.plugin_output);
            }
            if (_info_depth >= 3) {
                s.output(static_cast<int>(entry.last_hard_state));
                s.output(entry.current_attempt);
                s.output(entry.max_check_attempts);
                s.output(entry.scheduled_downtime_depth);
                s.output(static_cast<int>(entry.acknowledged));
                s.output(static_cast<int>(entry.service_period_active));
            }
        }
    }
}

std::vector<std::string> ServiceListColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    auto entries = getEntries(row, auth_user);
    std::vector<std::string> descriptions;
    std::transform(entries.begin(), entries.end(),
                   std::back_inserter(descriptions),
                   [](const auto &entry) { return entry.description; });
    return descriptions;
}

#ifndef CMC
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
    (void)_mc;  // HACK
    if (const auto *mem = columnData<Host::services_t>(row)) {
        for (const auto &svc : *mem) {
            if (auth_user == nullptr || svc->hasContact(auth_user)) {
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
            if (auth_user == nullptr ||
                is_authorized_for(_mc, auth_user, svc->host_ptr, svc)) {
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
                    inCustomTimeperiod(_mc, svc));
            }
        }
    }
#endif
    return entries;
}
