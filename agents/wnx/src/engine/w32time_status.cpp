// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/w32time_status.h"

#include <string>

namespace cma::provider {
std::string W32TimeStatus::makeBody() {
    auto cmd = wtools::ExpandStringWithEnvironment(
        L"%SystemRoot%\\System32\\w32tm.exe /query /status /verbose");
    auto data = wtools::oemToUtf8(wtools::RunCommand(cmd));
    if (data.empty()) {
        // special case: service not running|crashed
        // - we send _approximate_ error status
        // - we do not care about details as long known that service failed
        // - final decision what to do with that is left to the _check plugin_
        // - : is added to satisfy hack in check plugin
        return "Error: Windows time service is not running";
    }

    return data;
}
}  // namespace cma::provider
