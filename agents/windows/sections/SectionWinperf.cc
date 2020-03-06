// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionWinperf.h"
#include <algorithm>
#include <iomanip>
#include "Environment.h"
#include "Logger.h"
#include "PerfCounter.h"
#include "SectionHeader.h"
#include "stringutil.h"

SectionWinperf::SectionWinperf(const std::string &name, const Environment &env,
                               Logger *logger, const WinApiInterface &winapi)
    : Section("winperf_" + name, env, logger, winapi,
              std::make_unique<DefaultHeader>("winperf_" + name, logger))
    , _base(0) {}

SectionWinperf *SectionWinperf::withBase(unsigned int base) {
    _base = base;
    return this;
}

bool SectionWinperf::produceOutputInner(std::ostream &out,
                                        const std::optional<std::string> &) {
    Debug(_logger) << "SectionWinperf::produceOutputInner";
    try {
        PerfCounterObject counterObject(_base, _winapi, _logger);

        if (!counterObject.isEmpty()) {
            LARGE_INTEGER Frequency;
            _winapi.QueryPerformanceFrequency(&Frequency);
            out << std::fixed << std::setprecision(2)
                << section_helpers::current_time<std::chrono::milliseconds,
                                                 double>()
                << " " << _base << " " << Frequency.QuadPart << "\n";

            std::vector<PERF_INSTANCE_DEFINITION *> instances =
                counterObject.instances();
            // output instances - if any
            if (instances.size() > 0) {
                try {
                    out << instances.size() << " instances:";
                    for (std::wstring name : counterObject.instanceNames()) {
                        std::replace(name.begin(), name.end(), L' ', L'_');
                        out << " " << Utf8(name);
                    }
                    out << "\n";
                } catch (const std::range_error &e) {
                    // catch possible exception when UTF-16 is in not valid
                    // range for Linux toolchain,  see FEED-3048
                    Error(_logger)
                        << "Exception: " << e.what()
                        << " UTF-16 -> UTF-8 conversion error. Skipping line Win Perf.";
                }
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
