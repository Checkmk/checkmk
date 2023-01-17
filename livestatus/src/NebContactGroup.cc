// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebContactGroup.h"

#include "livestatus/StringUtils.h"

// Older Nagios headers are not const-correct... :-P
NebContactGroup::NebContactGroup(const std::string &name)
    : contact_group_{::find_contactgroup(const_cast<char *>(name.c_str()))} {}

// Older Nagios headers are not const-correct... :-P
bool NebContactGroup::isMember(const IContact &contact) const {
    return ::is_contact_member_of_contactgroup(
               const_cast<contactgroup *>(contact_group_),
               const_cast<::contact *>(
                   static_cast<const ::contact *>(contact.handle()))) != 0;
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
