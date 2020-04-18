// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceListStateColumn.h"
#include "LogEntry.h"
#include "Row.h"

#ifdef CMC
#include <memory>
#include "Service.h"
#include "State.h"
#else
#include "auth.h"
#endif

int32_t ServiceListStateColumn::getValue(Row row,
                                         const contact *auth_user) const {
#ifdef CMC
    if (auto p = columnData<Host::services_t>(row)) {
        return getValueFromServices(_mc, _logictype, p, auth_user);
    }
    return 0;
#else
    servicesmember *mem = nullptr;
    if (auto p = columnData<servicesmember *>(row)) {
        mem = *p;
    }
    return getValueFromServices(_mc, _logictype, mem, auth_user);
#endif
}

// static
int32_t ServiceListStateColumn::getValueFromServices(MonitoringCore *mc,
                                                     Type logictype,
                                                     service_list mem,
                                                     const contact *auth_user) {
    int32_t result = 0;
#ifdef CMC
    (void)mc;
    if (mem != nullptr) {
        for (const auto &svc : *mem) {
            if (auth_user == nullptr || svc->hasContact(auth_user)) {
                update(logictype, svc.get(), result);
            }
        }
    }
#else
    for (; mem != nullptr; mem = mem->next) {
        service *svc = mem->service_ptr;
        if (auth_user == nullptr ||
            is_authorized_for(mc, auth_user, svc->host_ptr, svc)) {
            update(logictype, svc, result);
        }
    }
#endif
    return result;
}

// static
void ServiceListStateColumn::update(Type logictype, service *svc,
                                    int32_t &result) {
#ifdef CMC
    uint32_t last_hard_state = svc->state()->_last_hard_state;
    uint32_t current_state = svc->state()->_current_state;
    bool has_been_checked = svc->state()->_has_been_checked;
#else
    int last_hard_state = svc->last_hard_state;
    int current_state = svc->current_state;
    bool has_been_checked = svc->has_been_checked != 0;
#endif
    int service_state;
    Type lt;
    if (static_cast<int>(logictype) >= 60) {
        service_state = last_hard_state;
        lt = static_cast<Type>(static_cast<int>(logictype) - 64);
    } else {
        service_state = current_state;
        lt = logictype;
    }
    switch (lt) {
        case Type::worst_state:
            if (worse(static_cast<ServiceState>(service_state),
                      static_cast<ServiceState>(result))) {
                result = service_state;
            }
            break;
        case Type::num:
            result++;
            break;
        case Type::num_pending:
            if (!has_been_checked) {
                result++;
            }
            break;
        default:
            if (has_been_checked && service_state == static_cast<int>(lt)) {
                result++;
            }
            break;
    }
}
