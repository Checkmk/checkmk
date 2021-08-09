// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostGroupsColumn.h"

#include "MonitoringCore.h"
#include "Row.h"
#include "auth.h"

#ifdef CMC
#include <unordered_set>

#include "Host.h"
#include "ObjectGroup.h"
#else
#include "nagios.h"
#endif

std::vector<std::string> HostGroupsColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    std::vector<std::string> group_names;
#ifdef CMC
    if (const auto *host = columnData<Host>(row)) {
        for (const auto *hg : host->groups()) {
            if (is_authorized_for_host_group(_mc->groupAuthorization(), hg,
                                             auth_user)) {
                group_names.push_back(hg->name());
            }
        }
    }
#else
    if (const auto *p = columnData<objectlist *>(row)) {
        for (objectlist *list = *p; list != nullptr; list = list->next) {
            auto *hg = static_cast<hostgroup *>(list->object_ptr);
            if (is_authorized_for_host_group(_mc->groupAuthorization(), hg,
                                             auth_user)) {
                group_names.emplace_back(hg->group_name);
            }
        }
    }
#endif
    return group_names;
}
