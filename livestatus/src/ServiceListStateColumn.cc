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
#include "auth.h"

int32_t ServiceListStateColumn::getValue(Row row,
                                         const contact *auth_user) const {
    servicesmember *mem = nullptr;
    if (auto p = columnData<servicesmember *>(row)) {
        mem = *p;
    }
    return getValueFromServices(_mc, _logictype, mem, auth_user);
}

// static
int32_t ServiceListStateColumn::getValueFromServices(MonitoringCore *mc,
                                                     Type logictype,
                                                     servicesmember *mem,
                                                     const contact *auth_user) {
    int32_t result = 0;
    for (; mem != nullptr; mem = mem->next) {
        service *svc = mem->service_ptr;
        if (auth_user == nullptr ||
            is_authorized_for(mc, auth_user, svc->host_ptr, svc)) {
            update(logictype, svc, result);
        }
    }
    return result;
}

// static
void ServiceListStateColumn::update(Type logictype, service *svc,
                                    int32_t &result) {
    int service_state;
    Type lt;
    if (static_cast<int>(logictype) >= 60) {
        service_state = svc->last_hard_state;
        lt = static_cast<Type>(static_cast<int>(logictype) - 64);
    } else {
        service_state = svc->current_state;
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
            if (svc->has_been_checked == 0) {
                result++;
            }
            break;
        default:
            if (svc->has_been_checked != 0 &&
                service_state == static_cast<int>(lt)) {
                result++;
            }
            break;
    }
}
