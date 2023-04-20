// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebServiceGroup_h
#define NebServiceGroup_h

#include <functional>

#include "NebService.h"
#include "livestatus/Interface.h"
#include "nagios.h"

class NebServiceGroup : public IServiceGroup {
public:
    explicit NebServiceGroup(const servicegroup &service_group)
        : service_group_{service_group} {}

    [[nodiscard]] const void *handle() const override {
        return &service_group_;
    }

    bool all(const std::function<bool(const IService &)> &pred) const override {
        for (const auto *member = service_group_.members; member != nullptr;
             member = member->next) {
            if (!pred(NebService{*member->service_ptr})) {
                return false;
            }
        }
        return true;
    }

private:
    const servicegroup &service_group_;
};

#endif  // NebServiceGroup_h
