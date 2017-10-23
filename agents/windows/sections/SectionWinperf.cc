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

#include "SectionWinperf.h"
#include <algorithm>
#include <iomanip>
#include "../Environment.h"
#include "../Logger.h"
#include "../PerfCounter.h"
#include "../stringutil.h"

extern double current_time();

SectionWinperf::SectionWinperf(const std::string &name, const Environment &env,
                               Logger *logger, const WinApiAdaptor &winapi)
    : Section("winperf_" + name, "winperf_" + name, env, logger, winapi)
    , _base(0) {}

SectionWinperf *SectionWinperf::withBase(unsigned int base) {
    _base = base;
    return this;
}

bool SectionWinperf::produceOutputInner(std::ostream &out) {
    try {
        PerfCounterObject counterObject(_base, _winapi);

        if (!counterObject.isEmpty()) {
            LARGE_INTEGER Frequency;
            _winapi.QueryPerformanceFrequency(&Frequency);
            out << std::fixed << std::setprecision(2) << current_time() << " "
                << _base << " " << Frequency.QuadPart << "\n";

            std::vector<PERF_INSTANCE_DEFINITION *> instances =
                counterObject.instances();
            // output instances - if any
            if (instances.size() > 0) {
                out << instances.size() << " instances:";
                for (std::wstring name : counterObject.instanceNames()) {
                    std::replace(name.begin(), name.end(), L' ', L'_');
                    out << " " << Utf8(name);
                }
                out << "\n";
            }

            // output counters
            for (const PerfCounter &counter : counterObject.counters()) {
                out << static_cast<int>(counter.titleIndex()) -
                           static_cast<int>(_base);

                for (ULONGLONG value : counter.values(instances)) {
                    out << " " << value;
                }
                out << " " << counter.typeName() << "\n";
            }
        }
        return true;
    } catch (const std::exception &e) {
        Error(_logger) << "Exception: " << e.what();
        return false;
    }
}
