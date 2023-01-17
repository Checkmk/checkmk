// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "NebHostGroup.h"

#include "NebHost.h"

NebHostGroup::NebHostGroup(const hostgroup &hg) {
    for (const auto *mem = hg.members; mem != nullptr; mem = mem->next) {
        hosts_.emplace_back(std::make_unique<NebHost>(*mem->host_ptr));
    }
}
