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
#include "Column.h"
#include "Row.h"
#include "auth.h"

static inline bool hst_state_is_worse(int32_t state1, int32_t state2) {
    if (state1 == 0) {
        return false;  // UP is worse than nothing
    }
    if (state2 == 0) {
        return true;  // everything else is worse then UP
    }
    if (state2 == 1) {
        return false;  // nothing is worse than DOWN
    }
    if (state1 == 1) {
        return true;  // state1 is DOWN, state2 not
    }
    return false;  // both are UNREACHABLE
}

hostsmember *HostListStateColumn::getMembers(Row row) const {
    if (auto p = columnData<void>(row)) {
        return *offset_cast<hostsmember *>(p, _offset);
    }
    return nullptr;
}

int32_t HostListStateColumn::getValue(Row row, contact *auth_user) const {
    int32_t result = 0;
    for (hostsmember *mem = getMembers(row); mem != nullptr; mem = mem->next) {
        host *hst = mem->host_ptr;
        if (auth_user == nullptr ||
            is_authorized_for(_mc, auth_user, hst, nullptr)) {
            switch (_logictype) {
                case Type::num_svc_pending:
                case Type::num_svc_ok:
                case Type::num_svc_warn:
                case Type::num_svc_crit:
                case Type::num_svc_unknown:
                case Type::num_svc:
                    result += ServiceListStateColumn::getValue(
                        _mc,
                        static_cast<ServiceListStateColumn::Type>(_logictype),
                        hst->services, auth_user);
                    break;

                case Type::worst_svc_state: {
                    int state = ServiceListStateColumn::getValue(
                        _mc,
                        static_cast<ServiceListStateColumn::Type>(_logictype),
                        hst->services, auth_user);
                    if (ServiceListStateColumn::svcStateIsWorse(state,
                                                                result)) {
                        result = state;
                    }
                    break;
                }

                case Type::num_hst_up:
                case Type::num_hst_down:
                case Type::num_hst_unreach:
                    if (hst->has_been_checked != 0 &&
                        hst->current_state ==
                            static_cast<int>(_logictype) -
                                static_cast<int>(Type::num_hst_up)) {
                        result++;
                    }
                    break;

                case Type::num_hst_pending:
                    if (hst->has_been_checked == 0) {
                        result++;
                    }
                    break;

                case Type::num_hst:
                    result++;
                    break;

                case Type::worst_hst_state:
                    if (hst_state_is_worse(hst->current_state, result)) {
                        result = hst->current_state;
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
    }
    return result;
}
