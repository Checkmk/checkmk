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
    if (auto p = columnData<std::unordered_set<Host *>>(row)) {
        for (auto hst : *p) {
            if (auth_user == nullptr || hst->hasContact(auth_user)) {
                update(hst, auth_user, result);
            }
        }
    }
#else
    if (auto p = columnData<hostsmember *>(row)) {
        for (hostsmember *mem = *p; mem != nullptr; mem = mem->next) {
            host *hst = mem->host_ptr;
            if (auth_user == nullptr ||
                is_authorized_for(_mc, auth_user, hst, nullptr)) {
                update(hst, auth_user, result);
            }
        }
    }
#endif
    return result;
}

void HostListStateColumn::update(host *hst, const contact *auth_user,
                                 int32_t &result) const {
#ifdef CMC
    ServiceListStateColumn::service_list services = &hst->_services;
    bool has_been_checked = hst->state()->_has_been_checked;
    auto current_state = static_cast<int>(hst->state()->_current_state);
#else
    ServiceListStateColumn::service_list services = hst->services;
    bool has_been_checked = hst->has_been_checked != 0;
    int current_state = hst->current_state;
#endif
    switch (_logictype) {
        case Type::num_svc_pending:
        case Type::num_svc_ok:
        case Type::num_svc_warn:
        case Type::num_svc_crit:
        case Type::num_svc_unknown:
        case Type::num_svc:
            result += ServiceListStateColumn::getValueFromServices(
                _mc, static_cast<ServiceListStateColumn::Type>(_logictype),
                services, auth_user);
            break;

        case Type::worst_svc_state: {
            int state = ServiceListStateColumn::getValueFromServices(
                _mc, static_cast<ServiceListStateColumn::Type>(_logictype),
                services, auth_user);
            if (worse(static_cast<ServiceState>(state),
                      static_cast<ServiceState>(result))) {
                result = state;
            }
            break;
        }

        case Type::num_hst_up:
        case Type::num_hst_down:
        case Type::num_hst_unreach:
            if (has_been_checked &&
                current_state == static_cast<int>(_logictype) -
                                     static_cast<int>(Type::num_hst_up)) {
                result++;
            }
            break;

        case Type::num_hst_pending:
            if (!has_been_checked) {
                result++;
            }
            break;

        case Type::num_hst:
            result++;
            break;

        case Type::worst_hst_state:
            if (worse(static_cast<HostState>(current_state),
                      static_cast<HostState>(result))) {
                result = current_state;
            }
            break;
        case Type::num_svc_hard_ok:
        case Type::num_svc_hard_warn:
        case Type::num_svc_hard_crit:
        case Type::num_svc_hard_unknown:
        case Type::worst_svc_hard_state:
            // TODO(sp) Why are these not handled?
            break;
    }
}
