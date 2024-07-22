// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/ServiceListState.h"

#include <functional>

#include "livestatus/Interface.h"
#include "livestatus/LogEntry.h"
#include "livestatus/User.h"

int32_t ServiceListState::operator()(const IHost &hst, const User &user) const {
    int32_t result{0};
    hst.all_of_services([this, &user, &result](const IService &svc) {
        update(svc, user, result);
        return true;
    });
    return result;
}

int32_t ServiceListState::operator()(const IServiceGroup &group,
                                     const User &user) const {
    int32_t result{0};
    group.all([this, &user, &result](const IService &svc) {
        update(svc, user, result);
        return true;
    });
    return result;
}

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
void ServiceListState::update(const IService &svc, const User &user,
                              int32_t &result) const {
    if (!user.is_authorized_for_service(svc)) {
        return;
    }
    auto current_state = static_cast<ServiceState>(svc.current_state());
    auto last_hard_state = static_cast<ServiceState>(svc.last_hard_state());
    auto has_been_checked = svc.has_been_checked();
    auto handled = svc.problem_has_been_acknowledged() ||
                   svc.scheduled_downtime_depth() > 0;
    switch (type_) {
        case Type::num:
            result++;
            break;
        case Type::num_pending:
            if (!has_been_checked) {
                result++;
            }
            break;
        case Type::num_handled_problems:
            if (has_been_checked && current_state != ServiceState::ok &&
                handled) {
                result++;
            }
            break;
        case Type::num_unhandled_problems:
            if (has_been_checked && current_state != ServiceState::ok &&
                !handled) {
                result++;
            }
            break;
        case Type::num_ok:
            if (has_been_checked && current_state == ServiceState::ok) {
                result++;
            }
            break;
        case Type::num_warn:
            if (has_been_checked && current_state == ServiceState::warning) {
                result++;
            }
            break;
        case Type::num_crit:
            if (has_been_checked && current_state == ServiceState::critical) {
                result++;
            }
            break;
        case Type::num_unknown:
            if (has_been_checked && current_state == ServiceState::unknown) {
                result++;
            }
            break;
        case Type::worst_state:
            if (worse(current_state, static_cast<ServiceState>(result))) {
                result = static_cast<int32_t>(current_state);
            }
            break;
        case Type::num_hard_ok:
            if (has_been_checked && last_hard_state == ServiceState::ok) {
                result++;
            }
            break;
        case Type::num_hard_warn:
            if (has_been_checked && last_hard_state == ServiceState::warning) {
                result++;
            }
            break;
        case Type::num_hard_crit:
            if (has_been_checked && last_hard_state == ServiceState::critical) {
                result++;
            }
            break;
        case Type::num_hard_unknown:
            if (has_been_checked && last_hard_state == ServiceState::unknown) {
                result++;
            }
            break;
        case Type::worst_hard_state:
            if (worse(last_hard_state, static_cast<ServiceState>(result))) {
                result = static_cast<int32_t>(last_hard_state);
            }
            break;
    }
}
