// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebServiceGroup.h"

#include <memory>

#include "NebService.h"
#include "nagios.h"

NebServiceGroup::NebServiceGroup(const servicegroup &sg) {
    for (const auto *mem = sg.members; mem != nullptr; mem = mem->next) {
        services_.emplace_back(std::make_unique<NebService>(*mem->service_ptr));
    }
}
