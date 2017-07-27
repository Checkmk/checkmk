// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "SectionMem.h"
#include <iomanip>
#include "../WinApiAdaptor.h"

SectionMem::SectionMem(const Environment &env, LoggerAdaptor &logger,
                       const WinApiAdaptor &winapi)
    : Section("mem", env, logger, winapi) {}

bool SectionMem::produceOutputInner(std::ostream &out) {
    typedef std::pair<const char *, DWORDLONG> KVPair;

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

    for (const auto &kv : {
             KVPair("MemTotal:", stat.ullTotalPhys),
             KVPair("MemFree:", stat.ullAvailPhys),
             KVPair("SwapTotal:", stat.ullTotalPageFile - stat.ullTotalPhys),
             KVPair("SwapFree:", stat.ullAvailPageFile - stat.ullAvailPhys),
             KVPair("PageTotal:", stat.ullTotalPageFile),
             KVPair("PageFree:", stat.ullAvailPageFile),
             KVPair("VirtualTotal:", stat.ullTotalVirtual),
             KVPair("VirtualFree:", stat.ullAvailVirtual),

         }) {
        out << std::setw(15) << std::left << kv.first << (kv.second / 1024)
            << " kB\n";
    }
    return true;
}
