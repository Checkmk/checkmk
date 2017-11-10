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

#include "SectionPerfcounter.h"
#include "../PerfCounter.h"
#include "../PerfCounterCommon.h"
#include "../logging.h"
#include "../stringutil.h"

SectionPerfcounter::SectionPerfcounter(const std::string &outputName,
                                       const std::string &configName,
                                       unsigned counterBaseNumber)
    : Section(outputName, configName), _counter_base_number(counterBaseNumber) {
    withSeparator(',');
}

SectionPerfcounter *SectionPerfcounter::withToggleIfMissing() {
    _toggle_if_missing = true;
    return this;
}

bool SectionPerfcounter::produceOutputInner(std::ostream &out,
                                            const Environment &) {
    try {
        PerfCounterObject counter_object(_counter_base_number);
        std::vector<std::wstring> instance_names =
            counter_object.instanceNames();
        std::vector<PERF_INSTANCE_DEFINITION *> instances =
            counter_object.instances();

        // we have to transpose the data coming from the perfcounter
        std::map<int, std::vector<std::wstring>> value_map;

        for (size_t i = 0; i < instances.size(); ++i) {
            value_map[i] = std::vector<std::wstring>();
        }

        for (const PerfCounter &counter : counter_object.counters()) {
            int idx = 0;
            for (ULONGLONG value : counter.values(instances)) {
                value_map[idx++].push_back(std::to_wstring(value));
            }
        }

        out << "instance,"
            << to_utf8(join(counter_object.counterNames(), L",").c_str())
            << "\n";
        for (const auto &instance_values : value_map) {
            std::wstring instance_name = L"\"\"";
            if (static_cast<size_t>(instance_values.first) <
                instance_names.size()) {
                instance_name = instance_names[instance_values.first];
            }
            out << to_utf8(instance_name.c_str()) << ","
                << to_utf8(join(instance_values.second, L",").c_str()) << "\n";
        }
    } catch (const std::exception &e) {
        crash_log("Exception: %s", e.what());
        return false;
    }
    return true;
}
