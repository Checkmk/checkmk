// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/HostListState.h"

#include <functional>

#include "livestatus/Interface.h"
#include "livestatus/LogEntry.h"
#include "livestatus/ServiceListState.h"
#include "livestatus/User.h"

int32_t HostListState::operator()(const IHostGroup &group,
                                  const User &user) const {
    int32_t result{0};
    group.all([this, &user, &result](const IHost &hst) {
        update(hst, user, result);
        return true;
    });
    return result;
}

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
void HostListState::update(const IHost &hst, const User &user,
                           int32_t &result) const {
    if (!user.is_authorized_for_host(hst)) {
        return;
    }
    auto current_state = static_cast<HostState>(hst.current_state());
    auto has_been_checked = hst.has_been_checked();
    auto handled = hst.problem_has_been_acknowledged() ||
                   hst.scheduled_downtime_depth() > 0;
    switch (type_) {
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
            result += ServiceListState{ServiceListState::Type::num}(hst, user);
            break;
        case Type::num_svc_pending:
            result += ServiceListState{ServiceListState::Type::num_pending}(
                hst, user);
            break;
        case Type::num_svc_handled_problems:
            result += ServiceListState{
                ServiceListState::Type::num_handled_problems}(hst, user);
            break;
        case Type::num_svc_unhandled_problems:
            result += ServiceListState{
                ServiceListState::Type::num_unhandled_problems}(hst, user);
            break;
        case Type::num_svc_ok:
            result +=
                ServiceListState{ServiceListState::Type::num_ok}(hst, user);
            break;
        case Type::num_svc_warn:
            result +=
                ServiceListState{ServiceListState::Type::num_warn}(hst, user);
            break;
        case Type::num_svc_crit:
            result +=
                ServiceListState{ServiceListState::Type::num_crit}(hst, user);
            break;
        case Type::num_svc_unknown:
            result += ServiceListState{ServiceListState::Type::num_unknown}(
                hst, user);
            break;
        case Type::worst_svc_state: {
            auto state = ServiceListState{ServiceListState::Type::worst_state}(
                hst, user);
            if (worse(static_cast<ServiceState>(state),
                      static_cast<ServiceState>(result))) {
                result = state;
            }
            break;
        }
        case Type::num_svc_hard_ok:
            result += ServiceListState{ServiceListState::Type::num_hard_ok}(
                hst, user);
            break;
        case Type::num_svc_hard_warn:
            result += ServiceListState{ServiceListState::Type::num_hard_warn}(
                hst, user);
            break;
        case Type::num_svc_hard_crit:
            result += ServiceListState{ServiceListState::Type::num_hard_crit}(
                hst, user);
            break;
        case Type::num_svc_hard_unknown:
            result += ServiceListState{
                ServiceListState::Type::num_hard_unknown}(hst, user);
            break;
        case Type::worst_svc_hard_state: {
            auto state = ServiceListState{
                ServiceListState::Type::worst_hard_state}(hst, user);
            if (worse(static_cast<ServiceState>(state),
                      static_cast<ServiceState>(result))) {
                result = state;
            }
            break;
        }
    }
}
