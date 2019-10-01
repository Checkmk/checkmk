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
