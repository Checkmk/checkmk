// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/system_time.h"

#include <string>

namespace cma::provider {

std::string SystemTime::makeBody() {
    const auto now = tools::SecondsSinceEpoch();
    return std::to_string(now) + "\n";
}

}  // namespace cma::provider
