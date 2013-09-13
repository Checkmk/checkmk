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

#include "ServiceSpecialDoubleColumn.h"
#include "nagios.h"
#include "logger.h"
#include "time.h"

extern int      interval_length;

double ServiceSpecialDoubleColumn::getValue(void *data)
{
    data = shiftPointer(data);
    if (!data) return 0;

    service *svc = (service *)data;
    switch (_type) {
        case SSDC_STALENESS:
        {
            bool is_cmk_passive = !strncmp(svc->check_command_ptr->name, "check_mk-", 9);

            time_t check_result_age = time(0) - svc->last_check;
            service *tmp_svc;

            // check_mk PASSIVE CHECK: Find check-mk service and get its check interval
            if (is_cmk_passive) {
                host *host = svc->host_ptr;
                servicesmember *svc_member = host->services;
                double check_interval = 1;
                while (svc_member != 0) {
                    tmp_svc = svc_member->service_ptr;
                    if (!strncmp(tmp_svc->check_command_ptr->name, "check-mk", 9)) {
                        return check_result_age / ((tmp_svc->check_interval == 0 ? 1 : tmp_svc->check_interval) * interval_length);
                    }
                    svc_member = svc_member->next;
                }
                return 1; // Shouldnt happen! We always except check-mk service
            }
            else // Other non-cmk passive and active checks
            {
                return check_result_age / ((svc->check_interval == 0 ? 1 : svc->check_interval) * interval_length);
            }
        }
    }
    return -1; // Never reached
}
