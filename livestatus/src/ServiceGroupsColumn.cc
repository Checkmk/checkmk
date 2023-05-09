// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ServiceGroupsColumn.h"

#include "Row.h"

#ifdef CMC
#include "Object.h"
#include "ObjectGroup.h"
#include "cmc.h"
#else
#include "MonitoringCore.h"
#include "auth.h"
#include "nagios.h"
#endif

std::vector<std::string> ServiceGroupsColumn::getValue(
    Row row, const contact *auth_user,
    std::chrono::seconds /*timezone_offset*/) const {
    std::vector<std::string> group_names;
#ifdef CMC
    (void)_mc;  // HACK
    if (const auto *object = columnData<Object>(row)) {
        for (const auto &og : object->_groups) {
            if (og->isContactAuthorized(auth_user)) {
                group_names.push_back(og->name());
            }
        }
    }
#else
    if (const auto *p = columnData<objectlist *>(row)) {
        for (objectlist *list = *p; list != nullptr; list = list->next) {
            auto *sg = static_cast<servicegroup *>(list->object_ptr);
            if (is_authorized_for_service_group(_mc->groupAuthorization(),
                                                _mc->serviceAuthorization(), sg,
                                                auth_user)) {
                group_names.emplace_back(sg->group_name);
            }
        }
    }
#endif
    return group_names;
}
