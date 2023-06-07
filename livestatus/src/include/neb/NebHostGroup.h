// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebHostGroup_h
#define NebHostGroup_h

#include <functional>

#include "livestatus/Interface.h"
#include "neb/NebHost.h"
#include "neb/nagios.h"

class NebHostGroup : public IHostGroup {
public:
    explicit NebHostGroup(const hostgroup &host_group)
        : host_group_{host_group} {}

    [[nodiscard]] const void *handle() const override { return &host_group_; }

    [[nodiscard]] std::string name() const override {
        return host_group_.group_name;
    }

    [[nodiscard]] std::string alias() const override {
        return host_group_.alias == nullptr ? "" : host_group_.alias;
    }
    [[nodiscard]] std::string notes() const override {
        return host_group_.notes == nullptr ? "" : host_group_.notes;
    }
    [[nodiscard]] std::string notes_url() const override {
        return host_group_.notes_url == nullptr ? "" : host_group_.notes_url;
    }
    [[nodiscard]] std::string action_url() const override {
        return host_group_.action_url == nullptr ? "" : host_group_.action_url;
    }

    bool all(const std::function<bool(const IHost &)> &pred) const override {
        for (const auto *member = host_group_.members; member != nullptr;
             member = member->next) {
            if (!pred(NebHost{*member->host_ptr})) {
                return false;
            }
        }
        return true;
    }

private:
    const hostgroup &host_group_;
};
#endif  // NebHostGroup_h
