// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/mem.h"

#include <string>

namespace cma::provider {

std::string Mem::makeBody() {
    MEMORYSTATUSEX stat;
    stat.dwLength = sizeof stat;
    ::GlobalMemoryStatusEx(&stat);
    constexpr uint32_t kilobyte = 1024;

    return fmt::format(
        "MemTotal:      {} kB\n"
        "MemFree:       {} kB\n"
        "SwapTotal:     {} kB\n"
        "SwapFree:      {} kB\n"
        "PageTotal:     {} kB\n"
        "PageFree:      {} kB\n"
        "VirtualTotal:  {} kB\n"
        "VirtualFree:   {} kB\n",
        stat.ullTotalPhys / kilobyte,                            // total
        stat.ullAvailPhys / kilobyte,                            // free
        (stat.ullTotalPageFile - stat.ullTotalPhys) / kilobyte,  // swap total
        (stat.ullAvailPageFile - stat.ullAvailPhys) / kilobyte,  // swap free
        stat.ullTotalPageFile / kilobyte,                        // paged total
        stat.ullAvailPageFile / kilobyte,                        // paged free
        stat.ullTotalVirtual / kilobyte,   // virtual total
        stat.ullAvailVirtual / kilobyte);  // virtual avail
}

}  // namespace cma::provider
