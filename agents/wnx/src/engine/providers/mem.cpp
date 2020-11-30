// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/mem.h"

#include <iostream>
#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::provider {

std::string Mem::makeBody() {
    MEMORYSTATUSEX stat;
    stat.dwLength = sizeof(stat);
    ::GlobalMemoryStatusEx(&stat);
    constexpr uint32_t kKilobyte = 1024;

    auto string = fmt::format(
        "MemTotal:      {} kB\n"
        "MemFree:       {} kB\n"
        "SwapTotal:     {} kB\n"
        "SwapFree:      {} kB\n"
        "PageTotal:     {} kB\n"
        "PageFree:      {} kB\n"
        "VirtualTotal:  {} kB\n"
        "VirtualFree:   {} kB\n",
        stat.ullTotalPhys / kKilobyte,                            // total
        stat.ullAvailPhys / kKilobyte,                            // free
        (stat.ullTotalPageFile - stat.ullTotalPhys) / kKilobyte,  // swap total
        (stat.ullAvailPageFile - stat.ullAvailPhys) / kKilobyte,  // swap free
        stat.ullTotalPageFile / kKilobyte,                        // paged total
        stat.ullAvailPageFile / kKilobyte,                        // paged free
        stat.ullTotalVirtual / kKilobyte,   // virtual total
        stat.ullAvailVirtual / kKilobyte);  // virtual avail

    return string;
}

};  // namespace cma::provider
