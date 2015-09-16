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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "ServicelistColumn.h"
#include "ServicelistColumnFilter.h"
#include "nagios.h"
#include "Query.h"
#include "TableServices.h"
#include "TimeperiodsCache.h"

extern TimeperiodsCache *g_timeperiods_cache;
extern TableServices *g_table_services;

servicesmember *ServicelistColumn::getMembers(void *data)
{
    data = shiftPointer(data);
    if (!data) return 0;

    return *(servicesmember **)((char *)data + _offset);
}

void ServicelistColumn::output(void *data, Query *query)
{
    query->outputBeginList();
    contact *auth_user = query->authUser();
    servicesmember *mem = getMembers(data);

    bool first = true;
    while (mem) {
        service *svc = mem->service_ptr;
        if (!auth_user || g_table_services->isAuthorized(auth_user, svc)) {
            if (!first)
                query->outputListSeparator();
            else
                first = false;
            // show only service name => no sublist
            if (!_show_host && _info_depth == 0)
                query->outputString(svc->description);
            else
            {
                query->outputBeginSublist();
                if (_show_host) {
                    query->outputString(svc->host_name);
                    query->outputSublistSeparator();
                }
                query->outputString(svc->description);
                if (_info_depth >= 1) {
                    query->outputSublistSeparator();
                    query->outputInteger(svc->current_state);
                    query->outputSublistSeparator();
                    query->outputInteger(svc->has_been_checked);
                }
                if (_info_depth >= 2) {
                    query->outputSublistSeparator();
                    query->outputString(svc->plugin_output);
                }
                if (_info_depth >= 3) {
                    query->outputSublistSeparator();
                    query->outputInteger(svc->last_hard_state);
                    query->outputSublistSeparator();
                    query->outputInteger(svc->current_attempt);
                    query->outputSublistSeparator();
                    query->outputInteger(svc->max_attempts);
                    query->outputSublistSeparator();
                    query->outputInteger(svc->scheduled_downtime_depth);
                    query->outputSublistSeparator();
                    query->outputInteger(svc->problem_has_been_acknowledged);
                    query->outputSublistSeparator();
                    query->outputInteger(inCustomTimeperiod(svc, "SERVICE_PERIOD"));
                }
                query->outputEndSublist();
            }
        }
        mem = mem->next;
    }
    query->outputEndList();
}

Filter *ServicelistColumn::createFilter(int opid, char *value)
{
    return new ServicelistColumnFilter(this, opid, value);
}


int ServicelistColumn::inCustomTimeperiod(service *svc, const char *varname)
{
    customvariablesmember *cvm = svc->custom_variables;
    while (cvm) {
        if (!(strcmp(cvm->variable_name, varname)))
            return g_timeperiods_cache->inTimeperiod(cvm->variable_value);
        cvm = cvm->next;
    }
    return 1; // assume 7X24
}
