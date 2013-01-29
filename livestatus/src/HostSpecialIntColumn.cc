// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "HostSpecialIntColumn.h"
#include "nagios.h"
#include "pnp4nagios.h"

int32_t HostSpecialIntColumn::getValue(void *data, Query *)
{
    data = shiftPointer(data);
    if (!data) return 0;

    host *hst = (host *)data;
    switch (_type) {
        case HSIC_REAL_HARD_STATE:
            if (hst->current_state == 0)
                return 0;
            else if (hst->state_type == 1)
                return hst->current_state; // we have reached a hard state
            else
                return hst->last_hard_state;
        case HSIC_PNP_GRAPH_PRESENT:
            return pnpgraph_present(hst->name, 0);
    }
    return -1; // never reached
}
