// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef W32TIME_PEERS
#define W32TIME_PEERS

#include <string>

#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {

class W32TimePeers final : public Synchronous {
public:
    W32TimePeers() : Synchronous(section::kW32TimePeers) {}
    W32TimePeers(const std::string &name, char separator)
        : Synchronous(name, separator) {}

private:
    std::string makeBody() override;
};

}  // namespace cma::provider

#endif  // W32TIME_PEERS
