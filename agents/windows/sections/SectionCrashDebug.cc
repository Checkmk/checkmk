// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

#include "SectionCrashDebug.h"

extern bool g_found_crash;
extern HANDLE g_crashlogMutex;
extern char g_crash_log[256];

SectionCrashDebug::SectionCrashDebug(Configuration &config)
  : Section("logwatch", "logwatch")
    , _crash_debug(config, "global", "crash_debug", false) {}

bool SectionCrashDebug::produceOutputInner(std::ostream &out,
                                           const Environment &) {
    if (*_crash_debug) {
        out << "[[[Check_MK Agent]]]\n";
        if (g_found_crash) {
            WaitForSingleObject(g_crashlogMutex, INFINITE);
            out << "C Check_MK Agent crashed\n";
            FILE *f = fopen(g_crash_log, "r");
            char line[1024];
            while (0 != fgets(line, sizeof(line), f)) {
                out << "W " << line;
            }
            ReleaseMutex(g_crashlogMutex);
            fclose(f);
            g_found_crash = false;
        }
    }
    return true;
}

