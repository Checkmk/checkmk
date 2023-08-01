// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebContactGroup_h
#define NebContactGroup_h

#include <string>

#include "livestatus/Interface.h"
#include "neb/nagios.h"

class NebContactGroup : public IContactGroup {
public:
    explicit NebContactGroup(const contactgroup &contact_group)
        : contact_group_{contact_group} {}

    [[nodiscard]] bool isMember(const IContact &contact) const override {
        // Older Nagios headers are not const-correct... :-P
        return ::is_contact_member_of_contactgroup(
                   const_cast<contactgroup *>(&contact_group_),
                   const_cast<::contact *>(
                       static_cast<const ::contact *>(contact.handle()))) != 0;
    }
    [[nodiscard]] std::string name() const override {
        return contact_group_.group_name;
    }

    [[nodiscard]] std::string alias() const override {
        return contact_group_.alias == nullptr ? "" : contact_group_.alias;
    }

    [[nodiscard]] std::vector<std::string> contactNames() const override {
        std::vector<std::string> names;
        for (const auto *cm = contact_group_.members; cm != nullptr;
             cm = cm->next) {
            names.emplace_back(cm->contact_ptr->name);
        }
        return names;
    }

private:
    const contactgroup &contact_group_;
};

#endif  // NebContactGroup_h
