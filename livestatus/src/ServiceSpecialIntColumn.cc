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

#include "ServiceSpecialIntColumn.h"
#include "Row.h"

#ifdef CMC
#include "Object.h"
#include "RRDInfoCache.h"
#include "State.h"
#include "cmc.h"
#else
#include "nagios.h"
#include "pnp4nagios.h"
#endif

int32_t ServiceSpecialIntColumn::getValue(
    Row row, const contact* /* auth_user */) const {
#ifdef CMC
    (void)_mc;
    if (auto object = columnData<Object>(row)) {
        switch (_type) {
            case Type::real_hard_state: {
                if (object->isCurrentStateOK()) {
                    return 0;
                }
                auto state = object->state();
                return state->_state_type == StateType::hard
                           ? state->_current_state
                           : state->_last_hard_state;
            }
            case Type::pnp_graph_present:
                return object->rrdInfo()._names.empty() ? 0 : 1;
        }
    }
#else
    if (auto svc = columnData<service>(row)) {
        switch (_type) {
            case Type::real_hard_state:
                if (svc->current_state == STATE_OK) {
                    return 0;
                }
                return svc->state_type == HARD_STATE ? svc->current_state
                                                     : svc->last_hard_state;
            case Type::pnp_graph_present:
                return pnpgraph_present(_mc, svc->host_ptr->name,
                                        svc->description);
        }
    }
#endif
    return 0;
}
