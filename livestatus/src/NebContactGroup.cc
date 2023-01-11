// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebContactGroup.h"

#include <memory>

#include "livestatus/Interface.h"
#include "livestatus/StringUtils.h"
#include "nagios.h"

bool NebContactGroup::isMember(const IContact &contact) const {
    return ::is_contact_member_of_contactgroup(
               ::find_contactgroup(const_cast<char *>(name_.c_str())),
               static_cast<::contact *>(
                   const_cast<void *>(contact.handle()))) != 0;
}

std::vector<std::unique_ptr<const IContactGroup>> ToIContactGroups(
    const std::string &group_sequence) {
    if (group_sequence.empty() || mk::ec::is_none(group_sequence)) {
        return {};
    }

    std::vector<std::unique_ptr<const IContactGroup>> groups;
    auto group_names{mk::ec::split_list(group_sequence)};
    groups.resize(group_names.size());
    for (const auto &n : group_names) {
        groups.emplace_back(std::make_unique<NebContactGroup>(n));
    }

    return groups;
}
