// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

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
            time_t check_result_age = time(0) - svc->last_check;
            if (svc->check_interval != 0)
                return check_result_age / (svc->check_interval * interval_length);

            // check_mk PASSIVE CHECK without check interval uses
            // the check interval of its check-mk service
            bool is_cmk_passive = !strncmp(svc->check_command_ptr->name, "check_mk-", 9);
            if (is_cmk_passive) {
                host *host = svc->host_ptr;
                service *tmp_svc;
                servicesmember *svc_member = host->services;
                while (svc_member != 0) {
                    tmp_svc = svc_member->service_ptr;
                    if (!strncmp(tmp_svc->check_command_ptr->name, "check-mk", 9)) {
                        return check_result_age / ((tmp_svc->check_interval == 0 ? 1 : tmp_svc->check_interval) * interval_length);
                    }
                    svc_member = svc_member->next;
                }
                return 1; // Shouldnt happen! We always expect a check-mk service
            }
            else // Other non-cmk passive and active checks without check_interval
            {
                return check_result_age / interval_length;
            }
        }
    }
    return -1; // Never reached
}
