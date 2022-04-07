// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostListState.h"

#include "auth.h"

#ifdef CMC
#include <memory>

#include "Host.h"
#include "State.h"
#endif

int32_t HostListState::operator()(const value_type &hsts,
                                  const User &user) const {
    int32_t result = 0;
#ifdef CMC
    for (const auto *hst : hsts) {
        if (user.is_authorized_for_host(*hst)) {
            const auto *state = hst->state();
            auto svcs = ServiceListState::value_type(hst->_services.size());
            for (const auto &s : hst->_services) {
                svcs.emplace(s.get());
            }
            update(user, static_cast<HostState>(state->current_state_),
                   state->has_been_checked_, svcs, hst->handled(), result);
        }
    }
#else
    for (hostsmember *mem = hsts; mem != nullptr; mem = mem->next) {
        host *hst = mem->host_ptr;
        if (user.is_authorized_for_host(*hst)) {
            update(user, static_cast<HostState>(hst->current_state),
                   hst->has_been_checked != 0, hst->services,
                   hst->problem_has_been_acknowledged != 0 ||
                       hst->scheduled_downtime_depth > 0,
                   result);
        }
    }
#endif
    return result;
}

void HostListState::update(const User &user, HostState current_state,
                           bool has_been_checked,
                           const ServiceListState::value_type &services,
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
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num, services);
            break;
        case Type::num_svc_pending:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_pending, services);
            break;
        case Type::num_svc_handled_problems:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_handled_problems, services);
            break;
        case Type::num_svc_unhandled_problems:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_unhandled_problems, services);
            break;
        case Type::num_svc_ok:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_ok, services);
            break;
        case Type::num_svc_warn:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_warn, services);
            break;
        case Type::num_svc_crit:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_crit, services);
            break;
        case Type::num_svc_unknown:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_unknown, services);
            break;
        case Type::worst_svc_state: {
            auto state = ServiceListState::getValueFromServices(
                user, ServiceListState::Type::worst_state, services);
            if (worse(static_cast<ServiceState>(state),
                      static_cast<ServiceState>(result))) {
                result = state;
            }
            break;
        }
        case Type::num_svc_hard_ok:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_hard_ok, services);
            break;
        case Type::num_svc_hard_warn:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_hard_warn, services);
            break;
        case Type::num_svc_hard_crit:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_hard_crit, services);
            break;
        case Type::num_svc_hard_unknown:
            result += ServiceListState::getValueFromServices(
                user, ServiceListState::Type::num_hard_unknown, services);
            break;
        case Type::worst_svc_hard_state: {
            auto state = ServiceListState::getValueFromServices(
                user, ServiceListState::Type::worst_hard_state, services);
            if (worse(static_cast<ServiceState>(state),
                      static_cast<ServiceState>(result))) {
                result = state;
            }
            break;
        }
    }
}
