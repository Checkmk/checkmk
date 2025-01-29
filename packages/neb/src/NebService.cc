// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "neb/NebService.h"

const IHost &NebService::host() const {
    return *core_.ihost(service_.host_ptr);
}

bool NebService::all_of_service_groups(
    std::function<bool(const IServiceGroup &)> pred) const {
    for (const auto *sg = service_.servicegroups_ptr; sg != nullptr;
         sg = sg->next) {
        if (!pred(*core_.iservicegroup(
                static_cast<const servicegroup *>(sg->object_ptr)))) {
            return false;
        }
    }
    return true;
}

bool NebService::all_of_contact_groups(
    std::function<bool(const IContactGroup &)> pred) const {
    for (const auto *cg = service_.contact_groups; cg != nullptr;
         cg = cg->next) {
        if (!pred(*core_.icontactgroup(cg->group_ptr))) {
            return false;
        }
    }
    return true;
}
