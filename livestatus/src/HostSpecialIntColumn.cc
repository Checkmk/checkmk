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

#include "HostSpecialIntColumn.h"
#include "MonitoringCore.h"
#include "Row.h"
#include "mk_inventory.h"

#ifdef CMC
#include "Host.h"
#include "Object.h"
#include "RRDInfo.h"
#include "State.h"
#include "cmc.h"
#else
#include "nagios.h"
#include "pnp4nagios.h"
#endif

int32_t HostSpecialIntColumn::getValue(Row row,
                                       const contact* /* auth_user */) const {
#ifdef CMC
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
                return object->rrdInfo().names_.empty() ? 0 : 1;
            case Type::mk_inventory_last:
                return static_cast<int32_t>(mk_inventory_last(
                    _mc->mkInventoryPath() + "/" + object->host()->name()));
        }
    }
#else
    if (auto hst = columnData<host>(row)) {
        switch (_type) {
            case Type::real_hard_state:
                if (hst->current_state == HOST_UP) {
                    return 0;
                }
                return hst->state_type == HARD_STATE ? hst->current_state
                                                     : hst->last_hard_state;
            case Type::pnp_graph_present:
                return pnpgraph_present(_mc, hst->name,
                                        dummy_service_description());
            case Type::mk_inventory_last:
                return static_cast<int32_t>(mk_inventory_last(
                    _mc->mkInventoryPath() + "/" + hst->name));
        }
    }
#endif
    return 0;
}
