// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/skype.h"

#include <string>
#include <string_view>

#include "common/wtools.h"
#include "providers/p_perf_counters.h"
#include "wnx/cfg.h"
#include "wnx/logger.h"

extern bool g_skype_testing;

namespace {
template <typename... T>
auto SkypeTestLog(const std::string &format, T... args) noexcept {
    if (g_skype_testing) {
        XLOG::l.i(format, args...);
    }
}
}  // namespace

namespace cma::provider {
// "sampletime,12321414,1231312\n"
std::string SkypeProvider::makeFirstLine() {
    return fmt::format("sampletime,{},{}\n", wtools::QueryPerformanceCo(),
                       wtools::QueryPerformanceFreq());
}

constexpr std::wstring_view g_skype_asp_some_counter{
    L"ASP.NET Apps v4.0.30319"};

// not const for tests. not const wstring because of STL
const std::vector<std::wstring> g_skype_counter_names{
    L"LS:WEB - Address Book Web Query",
    L"LS:WEB - Address Book File Download",
    L"LS:WEB - Location Information Service",
    L"LS:WEB - Distribution List Expansion",
    L"LS:WEB - UCWA",
    L"LS:WEB - Mobile Communication Service",
    L"LS:WEB - Throttling and Authentication",
    L"LS:WEB - Auth Provider related calls",
    L"LS:SIP - Protocol",
    L"LS:SIP - Responses",
    L"LS:SIP - Peers",
    L"LS:SIP - Load Management",
    L"LS:SIP - Authentication",
    L"LS:CAA - Operations",
    L"LS:DATAMCU - MCU Health And Performance",
    L"LS:AVMCU - MCU Health And Performance",
    L"LS:AsMcu - MCU Health And Performance",
    L"LS:ImMcu - MCU Health And Performance",
    L"LS:USrv - DBStore",
    L"LS:USrv - Conference Mcu Allocator",
    L"LS:JoinLauncher - Join Launcher Service Failures",
    L"LS:MediationServer - Health Indices",
    L"LS:MediationServer - Global Counters",
    L"LS:MediationServer - Global Per Gateway Counters",
    L"LS:MediationServer - Media Relay",
    L"LS:A/V Auth - Requests",
    L"LS:DATAPROXY - Server Connections",
    L"LS:XmppFederationProxy - Streams",
    L"LS:A/V Edge - TCP Counters",
    L"LS:A/V Edge - UDP Counters"
    //
};

namespace internal {
std::vector<std::wstring> *GetSkypeCountersVector() {
    return const_cast<std::vector<std::wstring> *>(&g_skype_counter_names);
}
std::wstring_view GetSkypeAspSomeCounter() { return g_skype_asp_some_counter; }
}  // namespace internal

namespace {
std::wstring GetCounters(
    const PERF_OBJECT_TYPE *object, std::wstring_view name,
    const std::vector<const PERF_COUNTER_DEFINITION *> &counters) {
    // first line generate
    std::wstring wide{L"[" + std::wstring(name) + L"]\ninstance"};

    // second line and data
    auto name_map = wtools::perf::GenerateNameMap();
    auto counter_names = wtools::perf::GenerateCounterNames(object, name_map);

    SkypeTestLog("scanning {} names and {} counters and map {}",
                 counter_names.size(), counters.size(), name_map.size());

    for (const auto &counter_name : counter_names) {
        SkypeTestLog("scanning {} name", wtools::ToUtf8(counter_name));
        wide += L"," + counter_name;
    }
    wide += L"\n";
    return wide;
}

void AddData(std::wstring &body,
             const std::vector<std::wstring> &instance_names,
             const std::vector<std::vector<ULONGLONG>> &columns) {
    const auto row_count = columns[0].size();
    SkypeTestLog("scanning {} columns, row_count is {}", columns.size(),
                 row_count);

    // Formatting
    // instance_name,value_0, value_1,...,value_last\n
    // .........
    // instance_name,value_0, value_1,...,value_last\n
    for (size_t row = 0; row < row_count; ++row) {
        auto instance_name =
            row < instance_names.size() ? instance_names[row] : L"\"\"";
        body += instance_name;

        for (const auto &column : columns) {
            body += L"," + std::to_wstring(column[row]);
        }
        body += L"\n";
    }
}
}  // namespace

// returns correct form table
// [LS:blabla]
// sampletime,123456, 63344
// instances,CounterA,CounterB
// Instance1, valueA1, valueB1
// Instance2, valueA2, valueB2
// empty string on absent data or error

std::wstring SkypeProvider::makeSubSection(std::wstring_view name) {
    namespace perf = wtools::perf;

    auto reg_name = wtools::ToUtf8(name);
    SkypeTestLog("Skype Perf Counter '{}'", reg_name);

    uint32_t key_index = 0;
    auto data = details::LoadWinPerfData(std::wstring(name), key_index);
    if (data.len_ == 0) {
        XLOG::t.w("Not found in registry Skype Perf Counter '{}'", reg_name);
        return {};
    }

    const auto *object = perf::FindPerfObject(data, key_index);
    if (object == nullptr) {
        SkypeTestLog("Not found index {}, for value '{}'", key_index, reg_name);
        return {};
    }
    SkypeTestLog("index {}, for value '{}'", key_index, reg_name);

    const PERF_COUNTER_BLOCK *block{nullptr};
    auto counters = perf::GenerateCounters(object, block);
    auto body = GetCounters(object, name, counters);

    // main table
    auto instance_names = perf::GenerateInstanceNames(object);
    auto instances = perf::GenerateInstances(object);

    std::vector<std::vector<ULONGLONG>> columns;
    for (const auto &counter : counters) {
        std::vector<ULONGLONG> v;
        if (instances.empty()) {
            v.emplace_back(perf::GetValueFromBlock(*counter, block));
        } else {
            v = perf::GenerateValues(*counter, instances);
        }
        SkypeTestLog("columns [{}] added [{}] values", columns.size(),
                     v.size());
        columns.push_back(v);
    }
    AddData(body, instance_names, columns);

    if (g_skype_testing) {
        return body;
    }

    return columns[0].empty() && !g_skype_testing ? L"" : body;
}

std::string SkypeProvider::makeBody() {
    std::wstring subsections;

    for (const auto &registry_name : g_skype_counter_names) {
        subsections += makeSubSection(registry_name);
    }

    if (subsections.empty() && !g_skype_testing) {
        return "";
    }

    subsections += makeSubSection(g_skype_asp_some_counter);
    return makeFirstLine() + wtools::ToUtf8(subsections);
}

}  // namespace cma::provider
