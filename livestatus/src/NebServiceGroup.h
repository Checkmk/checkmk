// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebServiceGroup_h
#define NebServiceGroup_h

#include <memory>
#include <vector>

#include "livestatus/Interface.h"
#include "nagios.h"
class NebServiceGroup : public IServiceGroup {
public:
    explicit NebServiceGroup(const servicegroup &sg);
    const std::vector<std::unique_ptr<const IService>> &services()
        const override {
        return services_;
    };

private:
    std::vector<std::unique_ptr<const IService>> services_;
};
#endif  // NebServiceGroup_h
