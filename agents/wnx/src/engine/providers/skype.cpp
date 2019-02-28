
// provides basic api to start and stop service
#include "stdafx.h"

#include <filesystem>
#include <regex>
#include <string>
#include <string_view>
#include <tuple>

#include "fmt/format.h"

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "common/wtools.h"

#include "cfg.h"
#include "cma_core.h"
#include "glob_match.h"

#include "logger.h"

#include "providers/p_perf_counters.h"
#include "providers/skype.h"

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

    uint32_t key_index = 0;
    auto data = details::LoadWinPerfData(RegName, key_index);
    if (data.len_ == 0) {
        XLOG::d("Not found in registry Skype Perf Counter '{}'",
                wtools::ConvertToUTF8(RegName));
        return {};
    }

    auto object = perf::FindPerfObject(data, key_index);
    if (!object) return {};

    // first line generate
    std::wstring wide = L"[" + std::wstring(RegName) + L"]\ninstances";

    // second line and data
    const PERF_COUNTER_BLOCK* block = nullptr;
    auto counters = wtools::perf::GenerateCounters(object, block);
    auto name_map = wtools::perf::GenerateNameMap();
    auto counter_names = perf::GenerateCounterNames(object, name_map);

    for (auto& counter_name : counter_names) {
        wide += L"," + counter_name;
    }
    wide += L"\n";

    // main table
    auto instance_names = wtools::perf::GenerateInstanceNames(object);
    auto instances = wtools::perf::GenerateInstances(object);

    std::vector<std::vector<ULONGLONG>> columns;
    for (const auto& counter : counters) {
        std::vector<ULONGLONG> v;
        if (instances.size() > 0) {
            v = perf::GenerateValues(*counter, instances);
        } else {
            v.emplace_back(perf::GetValueFromBlock(*counter, block));
        }
        columns.push_back(v);
    }

    for (size_t row = 0; row < columns[0].size(); row++) {
        auto instance_name = instances.size() ? instance_names[row] : L"";
        wide += L"\"" + instance_name + L"\"";  // "Instance" or ""

        for (auto column : columns) wide += L"," + std::to_wstring(column[row]);
        wide += L"\n";
    }
    if (columns[0].size() == 0) return {};

    return wide;
}

std::string SkypeProvider::makeBody() const {
    using namespace cma::cfg;
    XLOG::t(XLOG_FUNC + " entering");

    auto out_string = makeFirstLine();
    std::wstring wide;

    for (auto& registry_name : SkypeCounterNames) {
        // add only non empty sub sections
        wide += makeSubSection(registry_name);
    }

    if (wide.empty()) {
        return "";
    }

    // stupid? stupid. This is Windows and Legacy code.
    // #TODO make this code not such stupid. Thank you.
    wide += makeSubSection(SkypeAspSomeCounter);

    out_string += wtools::ConvertToUTF8(wide);

    return out_string;
}

}  // namespace cma::provider
