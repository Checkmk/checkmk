
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/skype.h"

#include <filesystem>
#include <regex>
#include <string>
#include <string_view>
#include <tuple>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"
#include "fmt/format.h"
#include "glob_match.h"
#include "logger.h"
#include "providers/p_perf_counters.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

extern bool G_SkypeTesting;

namespace cma::provider {

void SkypeProvider::loadConfig() {
    // we do not need config for skype(at least initially)
}

void SkypeProvider::updateSectionStatus() {
    // stub
    // the same - no need, still may be in the future
}

// "sampletime,12321414,1231312\n"
std::string SkypeProvider::makeFirstLine() {
    using namespace wtools;
    return fmt::format("sampletime,{},{}\n", QueryPerformanceCo(),
                       QueryPerformanceFreq());
}

std::wstring SkypeAspSomeCounter = L"ASP.NET Apps v4.0.30319";

std::vector<std::wstring> SkypeCounterNames{
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
    L"LS:A/V Edge - UDP Counters"};

namespace internal {
std::vector<std::wstring>* GetSkypeCountersVector() {
    return &SkypeCounterNames;
}
}  // namespace internal

// returns correct form table
// [LS:blabla]
// sampletime,123456, 63344
// instances,CounterA,CounterB
// Instance1, valueA1, valueB1
// Instance2, valueA2, valueB2
// empty string on absent data or error

std::wstring SkypeProvider::makeSubSection(const std::wstring& RegName) {
    using namespace wtools;

    auto reg_name = wtools::ConvertToUTF8(RegName);
    if (G_SkypeTesting) XLOG::d.t("Skyping Perf Counter '{}'", reg_name);

    uint32_t key_index = 0;
    auto data = details::LoadWinPerfData(RegName, key_index);
    if (data.len_ == 0) {
        XLOG::t.w("Not found in registry Skype Perf Counter '{}'", reg_name);
        return {};
    }

    auto object = perf::FindPerfObject(data, key_index);
    if (nullptr == object) {
        if (G_SkypeTesting)
            XLOG::d("Not found index {}, for value '{}'", key_index, reg_name);
        return {};
    }
    if (G_SkypeTesting)
        XLOG::d.t("index {}, for value '{}'", key_index, reg_name);

    // first line generate
    std::wstring wide = L"[" + std::wstring(RegName) + L"]\ninstance";

    // second line and data
    const PERF_COUNTER_BLOCK* block = nullptr;
    auto counters = perf::GenerateCounters(object, block);
    auto name_map = perf::GenerateNameMap();
    auto counter_names = perf::GenerateCounterNames(object, name_map);

    if (G_SkypeTesting)
        XLOG::d.t("scanning {} names and {} counters and map {}",
                  counter_names.size(), counters.size(), name_map.size());

    for (auto& counter_name : counter_names) {
        if (G_SkypeTesting)
            XLOG::d.t("scanning {} name", wtools::ConvertToUTF8(counter_name));
        wide += L"," + counter_name;
    }
    wide += L"\n";

    // main table
    auto instance_names = perf::GenerateInstanceNames(object);
    auto instances = perf::GenerateInstances(object);

    std::vector<std::vector<ULONGLONG>> columns;
    for (const auto& counter : counters) {
        std::vector<ULONGLONG> v;
        if (instances.empty()) {
            v.emplace_back(perf::GetValueFromBlock(*counter, block));
        } else {
            v = perf::GenerateValues(*counter, instances);
        }
        if (G_SkypeTesting)
            XLOG::d.t("columns[{}] added {} values", columns.size(), v.size());
        columns.push_back(v);
    }

    if (G_SkypeTesting) XLOG::d.t("scanning {} columns", columns.size());

    const auto row_count = columns[0].size();
    for (size_t row = 0; row < row_count; row++) {
        auto instance_name =
            row < instance_names.size() ? instance_names[row] : L"\"\"";
        wide += instance_name;  // Instance or ""

        for (auto column : columns) wide += L"," + std::to_wstring(column[row]);
        wide += L"\n";
    }
    if (G_SkypeTesting) {
        // always provide output
        XLOG::d.t("columns[0] size  is {}", columns[0].size());
        return wide;
    }

    return columns[0].empty() ? L"" : wide;
}

std::string SkypeProvider::makeBody() {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering");

    std::wstring wide;

    for (auto& registry_name : SkypeCounterNames) {
        // add only non empty sub sections
        wide += makeSubSection(registry_name);
    }

    if (!wide.empty() || G_SkypeTesting) {
        wide += makeSubSection(SkypeAspSomeCounter);

        auto out_string = makeFirstLine();
        out_string += wtools::ConvertToUTF8(wide);
        return out_string;
    }

    XLOG::t(XLOG_FUNC + " nothing");
    return "";
}

}  // namespace cma::provider
