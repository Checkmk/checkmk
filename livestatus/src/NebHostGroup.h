// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebHostGroup_h
#define NebHostGroup_h

#include <memory>
#include <vector>

#include "livestatus/Interface.h"
#include "nagios.h"
class NebHostGroup : public IHostGroup {
public:
    explicit NebHostGroup(const hostgroup &hg);
    const std::vector<std::unique_ptr<const IHost>> &hosts() const override {
        return hosts_;
    };

private:
    std::vector<std::unique_ptr<const IHost>> hosts_;
};
#endif  // NebHostGroup_h
