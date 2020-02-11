
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/mem.h"

#include <iostream>
#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::provider {

std::string Mem::makeBody() {
    // the log output disabled because it
    // may be quite annoying during realtime monitoring
    // XLOG::t(XLOG_FUNC + " entering");

    // windows
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
