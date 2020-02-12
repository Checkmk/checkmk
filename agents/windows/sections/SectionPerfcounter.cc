// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionPerfcounter.h"
#include "Environment.h"
#include "Logger.h"
#include "PerfCounter.h"
#include "PerfCounterCommon.h"
#include "SectionHeader.h"
#include "stringutil.h"

int NameBaseNumberMap::getCounterBaseNumber(const std::string &counterName) {
    // Fill name -> counter ID maps lazily when first needed.
    if (_nameIdMaps.empty()) {
        _nameIdMaps = {perf_name_map<char>(_winapi, false),
                       perf_name_map<char>(_winapi, true)};
    }

    for (const auto &nameIdMap : _nameIdMaps) {
        const auto it = nameIdMap.find(counterName);

        if (it != nameIdMap.end()) {
            return it->second;
        }
    }
    Debug(_logger) << "NameBaseNumberMap::getCounterBaseNumber "
                   << "could not resolve counter name " << counterName;
    return -1;
}

SectionPerfcounter::SectionPerfcounter(const std::string &outputName,
                                       const std::string &configName,
                                       const Environment &env,
                                       NameBaseNumberMap &nameNumberMap,
                                       Logger *logger,
                                       const WinApiInterface &winapi)
    : Section(configName, env, logger, winapi,
              std::make_unique<SubSectionHeader>(outputName, logger))
    , _nameNumberMap(nameNumberMap) {}

bool SectionPerfcounter::produceOutputInner(
    std::ostream &out, const std::optional<std::string> &) {
    Debug(_logger) << "SectionPerfcounter::produceOutputInner";
    try {
        const int counterBaseNumber =
            _nameNumberMap.getCounterBaseNumber(_configName);

        if (counterBaseNumber < 0) {
            return false;
        }

        PerfCounterObject counter_object(counterBaseNumber, _winapi, _logger);
        std::vector<std::wstring> instance_names =
            counter_object.instanceNames();
        std::vector<PERF_INSTANCE_DEFINITION *> instances =
            counter_object.instances();
        Debug(_logger) << "SectionPerfcounter::produceOutputInner: got "
                       << instance_names.size() << " instance names and "
                       << instances.size() << " instances.";
        // we have to transpose the data coming from the perfcounter
        std::map<int, std::vector<std::wstring>> value_map;

        for (size_t i = 0; i < instances.size(); ++i) {
            value_map[i] = std::vector<std::wstring>();
        }

        for (const auto &counter : counter_object.counters()) {
            int idx = 0;
            for (ULONGLONG value : counter.values(instances)) {
                value_map[idx++].push_back(std::to_wstring(value));
            }
        }

        out << "instance," << Utf8(join(counter_object.counterNames(), L","))
            << "\n";
        for (const auto &[index, values] : value_map) {
            std::wstring instance_name = L"\"\"";
            if (static_cast<size_t>(index) < instance_names.size()) {
                instance_name = instance_names[index];
            }
            out << Utf8(instance_name) << "," << Utf8(join(values, L","))
                << "\n";
        }
    } catch (const std::exception &e) {
        Error(_logger) << "Exception: " << e.what();
        return false;
    }
    return true;
}
