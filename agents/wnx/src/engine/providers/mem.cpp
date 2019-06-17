
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/mem.h"

#include <iostream>
#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma {

namespace provider {

std::string Mem::makeBody() {
    // the log output disabled because it
    // may be quite annoying during realtime monitoring
    // XLOG::t(XLOG_FUNC + " entering");

    // windows
    MEMORYSTATUSEX stat;
    stat.dwLength = sizeof(stat);
    ::GlobalMemoryStatusEx(&stat);

    auto string = fmt::format(
        "MemTotal:      {} kB\n"
        "MemFree:       {} kB\n"
        "SwapTotal:     {} kB\n"
        "SwapFree:      {} kB\n"
        "PageTotal:     {} kB\n"
        "PageFree:      {} kB\n"
        "VirtualTotal:  {} kB\n"
        "VirtualFree:   {} kB\n",
        stat.ullTotalPhys / 1024,                            // total
        stat.ullAvailPhys / 1024,                            // free
        (stat.ullTotalPageFile - stat.ullTotalPhys) / 1024,  // swap total
        (stat.ullAvailPageFile - stat.ullAvailPhys) / 1024,  // swap free
        stat.ullTotalPageFile / 1024,                        // paged total
        stat.ullAvailPageFile / 1024,                        // paged free
        stat.ullTotalVirtual / 1024,                         // virtual total
        stat.ullAvailVirtual / 1024);                        // virtual avail

    return string;
}

}  // namespace provider
};  // namespace cma
