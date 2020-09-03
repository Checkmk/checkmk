// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostListStateColumn.h"

#include "LogEntry.h"
#include "Row.h"

#ifdef CMC
#include <unordered_set>

#include "Host.h"
#include "State.h"
#else
#include "auth.h"
#endif

int32_t HostListStateColumn::getValue(Row row, const contact *auth_user) const {
    int32_t result = 0;
#ifdef CMC
    if (const auto *p = columnData<std::unordered_set<Host *>>(row)) {
        for (auto *hst : *p) {
            if (auth_user == nullptr || hst->hasContact(auth_user)) {
                const auto *state = hst->state();
                update(auth_user, static_cast<HostState>(state->_current_state),
                       state->_has_been_checked, &hst->_services,
                       state->_acknowledged ||
                           state->_scheduled_downtime_depth > 0,
                       result);
            }
        }
    }
#else
    if (const auto *p = columnData<hostsmember *>(row)) {
        for (hostsmember *mem = *p; mem != nullptr; mem = mem->next) {
            host *hst = mem->host_ptr;
            if (auth_user == nullptr ||
                is_authorized_for(_mc, auth_user, hst, nullptr)) {
                update(auth_user, static_cast<HostState>(hst->current_state),
                       hst->has_been_checked != 0, hst->services,
                       hst->problem_has_been_acknowledged != 0 ||
                           hst->scheduled_downtime_depth > 0,
                       result);
            }
        }
    }
#endif
    return result;
}

void HostListStateColumn::update(const contact *auth_user,
                                 HostState current_state, bool has_been_checked,
                                 ServiceListStateColumn::service_list services,
                                 bool handled, int32_t &result) const {
    switch (_logictype) {
        case Type::num_hst:
            result++;
            break;
        case Type::num_hst_pending:
            if (!has_been_checked) {
                result++;
            }
            break;
        case Type::num_hst_handled_problems:
            if (has_been_checked && current_state != HostState::up && handled) {
                result++;
            }
            break;
        case Type::num_hst_unhandled_problems:
            if (has_been_checked && current_state != HostState::up &&
                !handled) {
                result++;
            }
            break;
        case Type::num_hst_up:
            if (has_been_checked && current_state == HostState::up) {
                result++;
            }
            break;
        case Type::num_hst_down:
            if (has_been_checked && current_state == HostState::down) {
                result++;
            }
            break;
        case Type::num_hst_unreach:
            if (has_been_checked && current_state == HostState::unreachable) {
                result++;
            }
            break;
        case Type::worst_hst_state:
            if (worse(current_state, static_cast<HostState>(result))) {
                result = static_cast<int32_t>(current_state);
            }
            break;
        case Type::num_svc:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num, services, auth_user);
            break;
        case Type::num_svc_pending:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_pending, services,
                auth_user);
            break;
        case Type::num_svc_handled_problems:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_handled_problems,
                services, auth_user);
            break;
        case Type::num_svc_unhandled_problems:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_unhandled_problems,
                services, auth_user);
            break;
        case Type::num_svc_ok:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_ok, services, auth_user);
            break;
        case Type::num_svc_warn:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_warn, services,
                auth_user);
            break;
        case Type::num_svc_crit:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_crit, services,
                auth_user);
            break;
        case Type::num_svc_unknown:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_unknown, services,
                auth_user);
            break;
        case Type::worst_svc_state: {
            auto state = ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::worst_state, services,
                auth_user);
            if (worse(static_cast<ServiceState>(state),
                      static_cast<ServiceState>(result))) {
                result = state;
            }
            break;
        }
        case Type::num_svc_hard_ok:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_hard_ok, services,
                auth_user);
            break;
        case Type::num_svc_hard_warn:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_hard_warn, services,
                auth_user);
            break;
        case Type::num_svc_hard_crit:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_hard_crit, services,
                auth_user);
            break;
        case Type::num_svc_hard_unknown:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::num_hard_unknown, services,
                auth_user);
            break;
        case Type::worst_svc_hard_state: {
            auto state = ServiceListStateColumn::getValueFromServices(
                _mc, ServiceListStateColumn::Type::worst_hard_state, services,
                auth_user);
            if (worse(static_cast<ServiceState>(state),
                      static_cast<ServiceState>(result))) {
                result = state;
            }
            break;
        }
    }
}
