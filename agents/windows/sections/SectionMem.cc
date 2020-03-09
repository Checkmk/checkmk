// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionMem.h"
#include <iomanip>
#include "Logger.h"
#include "SectionHeader.h"

SectionMem::SectionMem(const Environment &env, Logger *logger,
                       const WinApiInterface &winapi)
    : Section("mem", env, logger, winapi,
              std::make_unique<DefaultHeader>("mem", logger)) {}

bool SectionMem::produceOutputInner(std::ostream &out,
                                    const std::optional<std::string> &) {
    Debug(_logger) << "SectionMem::produceOutputInner";
    using KVPair = std::pair<const char *, DWORDLONG>;

    MEMORYSTATUSEX stat;
    stat.dwLength = sizeof(stat);
    _winapi.GlobalMemoryStatusEx(&stat);

    // The output imitates that of the Linux agent. That makes
    // a special check for check_mk unneccessary:
    // <<<mem>>>.
    // MemTotal:       514104 kB
    // MemFree:         19068 kB
    // SwapTotal:     1048568 kB
    // SwapFree:      1043732 kB

    for (const auto &[label, value] : {
             KVPair("MemTotal:", stat.ullTotalPhys),
             KVPair("MemFree:", stat.ullAvailPhys),
             KVPair("SwapTotal:", stat.ullTotalPageFile - stat.ullTotalPhys),
             KVPair("SwapFree:", stat.ullAvailPageFile - stat.ullAvailPhys),
             KVPair("PageTotal:", stat.ullTotalPageFile),
             KVPair("PageFree:", stat.ullAvailPageFile),
             KVPair("VirtualTotal:", stat.ullTotalVirtual),
             KVPair("VirtualFree:", stat.ullAvailVirtual),

         }) {
        out << std::setw(15) << std::left << label << (value / 1024) << " kB\n";
    }
    return true;
}
