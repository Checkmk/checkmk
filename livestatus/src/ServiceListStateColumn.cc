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
