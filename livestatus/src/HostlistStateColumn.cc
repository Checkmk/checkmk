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

#include "HostlistStateColumn.h"
#include "ServicelistStateColumn.h"
#include "nagios.h"
#include "TableServices.h"
#include "Query.h"

extern TableServices *g_table_hosts;


inline bool hst_state_is_worse(int32_t state1, int32_t state2)
{
    if (state1 == 0) return false;        // UP is worse than nothing
    else if (state2 == 0) return true;    // everything else is worse then UP
    else if (state2 == 1) return false;   // nothing is worse than DOWN
    else if (state1 == 1) return true;    // state1 is DOWN, state2 not
    else return false;                    // both are UNREACHABLE
}

hostsmember *HostlistStateColumn::getMembers(void *data)
{
    data = shiftPointer(data);
    if (!data) return 0;

    return *(hostsmember **)((char *)data + _offset);
}

int32_t HostlistStateColumn::getValue(void *data, Query *query)
{
    contact *auth_user = query->authUser();
    hostsmember *mem = getMembers(data);
    int32_t result = 0;
    int state;

    while (mem) {
        host *hst = mem->host_ptr;
        if (!auth_user || g_table_hosts->isAuthorized(auth_user, hst)) {
            switch (_logictype) {
                case HLSC_NUM_SVC_PENDING:
                case HLSC_NUM_SVC_OK:
                case HLSC_NUM_SVC_WARN:
                case HLSC_NUM_SVC_CRIT:
                case HLSC_NUM_SVC_UNKNOWN:
                case HLSC_NUM_SVC:
                    result += ServicelistStateColumn::getValue(_logictype, hst->services, query);
                    break;

                case HLSC_WORST_SVC_STATE:
                    state = ServicelistStateColumn::getValue(_logictype, hst->services, query);
                    if (ServicelistStateColumn::svcStateIsWorse(state, result))
                        result = state;
                    break;

                case HLSC_NUM_HST_UP:
                case HLSC_NUM_HST_DOWN:
                case HLSC_NUM_HST_UNREACH:
                    if (hst->has_been_checked && hst->current_state == _logictype - HLSC_NUM_HST_UP)
                        result ++;
                    break;

                case HLSC_NUM_HST_PENDING:
                    if (!hst->has_been_checked)
                        result ++;
                    break;

                case HLSC_NUM_HST:
                    result ++;
                    break;

                case HLSC_WORST_HST_STATE:
                    if (hst_state_is_worse(hst->current_state, result))
                        result = hst->current_state;
                    break;
            }
        }
        mem = mem->next;
    }
    return result;
}

