// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "w32time_status.h"

#include <string>

namespace cma::provider {
std::string W32TimeStatus::makeBody() {
    return "Test output for w32time_status section";
}
}  // namespace cma::provider
