// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebContactGroup_h
#define NebContactGroup_h

#include <string>

#include "livestatus/Interface.h"
#include "nagios.h"

class NebContactGroup : public IContactGroup {
public:
    // Older Nagios headers are not const-correct... :-P
    explicit NebContactGroup(const std::string &name)
        : contact_group_{
              ::find_contactgroup(const_cast<char *>(name.c_str()))} {}
    [[nodiscard]] const void *handle() const override { return contact_group_; }
    // Older Nagios headers are not const-correct... :-P
    [[nodiscard]] bool isMember(const IContact &contact) const override {
        return ::is_contact_member_of_contactgroup(
                   const_cast<contactgroup *>(contact_group_),
                   const_cast<::contact *>(
                       static_cast<const ::contact *>(contact.handle()))) != 0;
    }

private:
    const contactgroup *contact_group_;
};

#endif  // NebContactGroup_h
