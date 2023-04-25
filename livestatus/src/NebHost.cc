// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebHost.h"

#include <algorithm>
#include <string>
#include <unordered_map>
#include <utility>

#include "NebContactGroup.h"
#include "NebHostGroup.h"
#include "NebService.h"
#include "livestatus/Interface.h"
#include "nagios.h"
using namespace std::string_literals;

bool NebHost::all_of_parents(std::function<bool(const IHost &)> pred) const {
    for (const auto *h = host_.parent_hosts; h != nullptr; h = h->next) {
        if (!pred(NebHost{*h->host_ptr})) {
            return false;
        }
    }
    return true;
}
bool NebHost::all_of_children(std::function<bool(const IHost &)> pred) const {
    for (const auto *h = host_.child_hosts; h != nullptr; h = h->next) {
        if (!pred(NebHost{*h->host_ptr})) {
            return false;
        }
    }
    return true;
}
bool NebHost::all_of_host_groups(
    std::function<bool(const IHostGroup &)> pred) const {
    for (const auto *hg = host_.hostgroups_ptr; hg != nullptr; hg = hg->next) {
        if (!pred(NebHostGroup{
                *static_cast<const hostgroup *>(hg->object_ptr)})) {
            return false;
        }
    }
    return true;
}
bool NebHost::all_of_contact_groups(
    std::function<bool(const IContactGroup &)> pred) const {
    for (const auto *cg = host_.contact_groups; cg != nullptr; cg = cg->next) {
        if (!pred(NebContactGroup{*cg->group_ptr})) {
            return false;
        }
    }
    return true;
}

bool NebHost::all_of_labels(
    const std::function<bool(const Attribute &)> &pred) const {
    // TODO(sp) Avoid construction of temporary map
    auto labels =
        CustomAttributes(host_.custom_variables, AttributeKind::labels);
    return std::all_of(
        labels.cbegin(), labels.cend(),
        [&pred](const std::pair<std::string, std::string> &label) {
            return pred(Attribute{label.first, label.second});
        });
}

bool NebHost::all_of_services(
    std::function<bool(const IService &)> pred) const {
    for (const auto *s = host_.services; s != nullptr; s = s->next) {
        if (!pred(NebService{*s->service_ptr})) {
            return false;
        }
    }
    return true;
}
