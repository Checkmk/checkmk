// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/w32time_peers.h"

#include <string>

namespace cma::provider {
std::string W32TimePeers::makeBody() {
    return "Test output for w32time_peers section";
}
}  // namespace cma::provider
