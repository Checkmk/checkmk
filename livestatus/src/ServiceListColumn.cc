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

#include "ServiceListColumn.h"
#include <algorithm>
#include <iterator>
#include "Renderer.h"
#include "Row.h"

#ifdef CMC
#include <cstdint>
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
    if (auto mem = columnData<Host::services_t>(row)) {
        for (auto &svc : *mem) {
            if (auth_user == nullptr || svc->hasContact(auth_user)) {
                entries.emplace_back(
                    svc->name(),
                    static_cast<ServiceState>(svc->state()->_current_state),
                    svc->state()->_has_been_checked,
                    svc->state()->_plugin_output,
                    static_cast<ServiceState>(svc->state()->_last_hard_state),
                    svc->state()->_current_attempt, svc->_max_check_attempts,
                    svc->state()->_scheduled_downtime_depth,
                    svc->state()->_acknowledged,
                    svc->_service_period->isActive());
            }
        }
    }
#else
    if (auto p = columnData<servicesmember *>(row)) {
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
