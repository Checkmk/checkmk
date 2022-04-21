// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/perf_cpuload.h"

#include <pdh.h>
#include <pdhmsg.h>

#include <ranges>
#include <string_view>
#include <unordered_map>

#include "cfg.h"
#include "common/wtools.h"
#include "providers/p_perf_counters.h"
#include "section_header.h"
#include "tools/_misc.h"

#pragma comment(lib, "pdh.lib")

namespace rs = std::ranges;

constexpr std::wstring_view kProcessorQueueLength{
    L"\\System\\Processor Queue Length"};
uint64_t ReadSingleCounter(std::wstring_view path) {
    PDH_HQUERY query{nullptr};
    if (::PdhOpenQuery(NULL, 0, &query) != ERROR_SUCCESS) {
        XLOG::l("Failed PdhOpenQuery [{}]", ::GetLastError());
        return 0u;
    }
    ON_OUT_OF_SCOPE(::PdhCloseQuery(query));

    PDH_HCOUNTER counter{nullptr};
    DWORD type{0u};
    PDH_RAW_COUNTER value;
    if (::PdhAddCounter(query, path.data(), 0, &counter) == ERROR_SUCCESS &&
        ::PdhCollectQueryData(query) == ERROR_SUCCESS &&
        ::PdhGetRawCounterValue(counter, &type, &value) == ERROR_SUCCESS) {
        return static_cast<uint64_t>(value.FirstValue);
    }
    return 0u;
}

namespace cma::provider {

std::unordered_map<std::string, std::string> GetProcessorInfo(
    const std::vector<std::string> &names, std::wstring_view separator) {
    wtools::WmiWrapper wmi;

    if (!wmi.open() || !wmi.connect(kWmiPathStd)) {
        XLOG::l(XLOG_FUNC + " can't access WMI");
        return {};
    }
    wmi.impersonate();

    auto [table, ignored] = wmi.queryTable({}, L"Win32_Processor", separator,
                                           cfg::groups::global.getWmiTimeout());
    auto rows = tools::SplitString(table, L"\n");
    auto all_names = tools::SplitString(rows[0], separator);
    // case when last value is empty
    if (rows[1].back() == separator[0]) {
        rows[1] += separator[0];
    }
    auto all_values = tools::SplitString(rows[1], separator);
    if (all_names.size() != all_values.size()) {
        XLOG::l("Mismatching of values and names in GetProcessorInfo");
        return {};
    }
    std::unordered_map<std::string, std::string> result;
    for (const auto &n : names) {
        auto i = rs::find(all_names, wtools::ConvertToUTF16(n));
        if (i == all_names.end()) {
            XLOG::l.t("Not found {}", n);
            result[n] = "";
        } else {
            auto offset = i - all_names.begin();
            XLOG::l.t("Found {} at {}", n, offset);
            result[n] = fmt::format("{}", wtools::ToUtf8(all_values[offset]));
        }
    }

    return result;
}

std::string PerfCpuLoad::makeBody() {
    static const std::vector<std::string> names{"NumberOfLogicalProcessors",
                                                "NumberOfProcessors"};
    auto sep = wtools::ConvertToUTF16(fmt::format("{}", separator()));
    auto values = GetProcessorInfo(names, sep);
    auto processor_queue_length = ReadSingleCounter(kProcessorQueueLength);
    auto perf_time = wtools::QueryPerformanceCo();
    auto perf_freq = wtools::QueryPerformanceFreq();
    std::string out{section::MakeSubSectionHeader(kSubSectionSystemPerf)};
    out += fmt::format(
        "ProcessorQueueLength{0}Timestamp_PerfTime{0}Frequency_PerfTime{0}WMIStatus\n",
        kSepChar);
    out += fmt::format("{1}{0}{2}{0}{3}{0}OK\n", separator(),
                       processor_queue_length, perf_time, perf_freq);
    out += section::MakeSubSectionHeader(kSubSectionComputerSystem);
    for (const auto &n : names) {
        out += n + separator();
    }
    out += "WMIStatus\n";

    for (const auto &n : names) {
        out += (values.contains(n) ? values.at(n) : "") + separator();
    }
    out += "OK\n";

    return out;
}
};  // namespace cma::provider
