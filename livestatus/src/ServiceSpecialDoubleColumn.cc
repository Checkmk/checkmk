// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceSpecialDoubleColumn.h"

#include "Row.h"

#ifdef CMC
#include "HostSpecialDoubleColumn.h"
class Object;
#else
#include <cstring>
#include <ctime>

#include "nagios.h"
#endif

double ServiceSpecialDoubleColumn::getValue(Row row) const {
#ifdef CMC
    if (const auto *object = columnData<Object>(row)) {
        return HostSpecialDoubleColumn::staleness(object);
    }
#else
    if (const auto *svc = columnData<service>(row)) {
        extern int interval_length;
        auto check_result_age =
            static_cast<double>(time(nullptr) - svc->last_check);
        if (svc->check_interval != 0) {
            return check_result_age / (svc->check_interval * interval_length);
        }

        // check_mk PASSIVE CHECK without check interval uses the check
        // interval of its check-mk service
        bool is_cmk_passive =
            strncmp(svc->check_command_ptr->name, "check_mk-", 9) == 0;
        if (is_cmk_passive) {
            host *host = svc->host_ptr;
            for (servicesmember *svc_member = host->services;
                 svc_member != nullptr; svc_member = svc_member->next) {
                service *tmp_svc = svc_member->service_ptr;
                if (strncmp(tmp_svc->check_command_ptr->name, "check-mk", 8) ==
                    0) {
                    return check_result_age / ((tmp_svc->check_interval == 0
                                                    ? 1
                                                    : tmp_svc->check_interval) *
                                               interval_length);
                }
            }
            // Shouldn't happen! We always expect a check-mk service
            return 1;
        }
        // Other non-cmk passive and active checks without
        // check_interval
        return check_result_age / interval_length;
    }
#endif
    return 0;
}
