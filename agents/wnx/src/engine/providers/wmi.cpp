// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/wmi.h"

#include <chrono>
#include <iostream>
#include <string>
#include <unordered_map>

#include "common/cfg_info.h"
#include "tools/_raii.h"
#include "wnx/cfg.h"

using namespace std::string_literals;
namespace rs = std::ranges;

// controls behavior, we may want in the future,  works with older servers
// normally always true
constexpr bool g_add_wmi_status_column = true;

namespace cma::provider {
bool IsHeaderless(std::string_view name) noexcept { return name == kMsExch; }

/// use cache if body is empty(typical for new client, which returns empty on
/// timeout) post process result
/// update cache if data ok(not empty)
std::string WmiCachedDataHelper(std::string &cache_data,
                                const std::string &wmi_data, char separator) {
    // for very old servers
    if constexpr (!g_add_wmi_status_column) {
        return wmi_data;
    }

    if (!wmi_data.empty()) {
        // return original data with added OK in right column
        cache_data = wmi_data;  // store
        return wtools::WmiPostProcess(wmi_data, wtools::StatusColumn::ok,
                                      separator);
    }

    // we try to return cache with added "timeout" in last column
    if (!cache_data.empty()) {
        return wtools::WmiPostProcess(cache_data, wtools::StatusColumn::timeout,
                                      separator);
    }

    XLOG::d.t(XLOG_FUNC + " no data to provide, cache is also empty");
    return {};
}
namespace {
// ["Name", [Value1,Value2,...] ]
// ["msexch", [msexch_shit1, msexch_shit2] ] <-example
using NamedWideStringVector =
    std::unordered_map<std::string, std::vector<std::wstring>>;

using NamedStrVector =
    std::unordered_map<std::string, std::vector<std::string_view>>;

/// Description of wmi source
// for example "Root\\Cimv2" and "Win32_PerfRawData_W3SVC_WebService"
struct WmiSource {
    std::wstring name_space;
    std::wstring object_name;
    std::vector<std::wstring> service_names;
};

#if 0
/// reference
const std::vector<std::wstring> msexch_service_all_names = {
    L"MSExchangeADTopology",
    L"MSExchangeAntispamUpdate",
    L"MSExchangeCompliance",
    L"MSExchangeDagMgmt",
    L"MSExchangeDelivery",
    L"MSExchangeDiagnostics",
    L"MSExchangeEdgeSync",
    L"MSExchangeFastSearch",
    L"MSExchangeFrontEndTransport",
    L"MSExchangeHM",
    L"MSExchangeHMRecovery",
    L"MSExchangeImap4",
    L"MSExchangeIMAP4BE",
    L"MSExchangeIS",
    L"MSExchangeMailboxAssistants",
    L"MSExchangeMailboxReplication",
    L"MSExchangeMitigation",
    L"MSExchangeNotificationsBroker",
    L"MSExchangePop3",
    L"MSExchangePOP3BE",
    L"MSExchangeRepl",
    L"MSExchangeRPC",
    L"MSExchangeServiceHost",
    L"MSExchangeSubmission",
    L"MSExchangeThrottling",
    L"MSExchangeTransport",
    L"MSExchangeTransportLogSearch",
    L"MSExchangeUM",
    L"MSExchangeUMCR",
};
#endif
const std::vector<std::wstring> msexch_service_reasonable_names = {
    L"MSExchangeDiagnostics",
    L"MSExchangeHM",
    L"MSExchangeServiceHost",
    L"MSExchangeTransport",
};

// Link section name and WmiSource
using NamedWmiSources = std::unordered_map<std::string, WmiSource>;

// We configure our provider using static table with strings
const NamedWmiSources g_section_objects = {
    {std::string{kDotNetClrMemory},  //
     {
         .name_space{kWmiPathStd},
         .object_name{L"Win32_PerfRawData_NETFramework_NETCLRMemory"},
         .service_names{},
     }},
    {std::string{kWmiWebservices},  //
     {
         .name_space{kWmiPathStd},
         .object_name{L"Win32_PerfRawData_W3SVC_WebService"},
         .service_names{
             L"AppHostSvc",  // Application Host Helper Service IIS 7
             L"WAS",         // Windows Process Activation Service IIS 6
             L"W3SVC",       // World Wide Web Publishing Service IIS ?
         },
     }},
    {std::string{kOhm},  //
     {
         .name_space{kWmiPathOhm},
         .object_name{L"Sensor"},
         .service_names{},
     }},
    {std::string{kBadWmi},  // used for a testing
     {
         .name_space{L"Root\\BadWmiPath"},
         .object_name{L"BadSensor"},
         .service_names{},
     }},
    {"OhmBad"s,  // used for a testing
     {
         .name_space{kWmiPathOhm},
         .object_name{L"BadSensor"},
         .service_names{},
     }},
    {"system_perf"s,  // WMI CPULOAD group
     {
         .name_space{kWmiPathStd},
         .object_name{L"Win32_PerfRawData_PerfOS_System"},
         .service_names{},
     }},
    {"computer_system"s,  //
     {
         .name_space{kWmiPathStd},
         .object_name{L"Win32_ComputerSystem"},
         .service_names{},
     }},
    {"msexch_activesync"s,
     {
         .name_space{kWmiPathStd},
         .object_name{
             L"Win32_PerfRawData_MSExchangeActiveSync_MSExchangeActiveSync"},
         .service_names{msexch_service_reasonable_names},
     }},
    {"msexch_availability"s,  // MSEXCHANGE group
     {
         .name_space{kWmiPathStd},
         .object_name{
             L"Win32_PerfRawData_MSExchangeAvailabilityService_MSExchangeAvailabilityService"},
         .service_names{msexch_service_reasonable_names},
     }},
    {"msexch_owa"s,  //
     {
         .name_space{kWmiPathStd},
         .object_name{L"Win32_PerfRawData_MSExchangeOWA_MSExchangeOWA"},
         .service_names{msexch_service_reasonable_names},
     }},
    {"msexch_autodiscovery"s,
     {
         .name_space{kWmiPathStd},
         .object_name{
             L"Win32_PerfRawData_MSExchangeAutodiscover_MSExchangeAutodiscover"},
         .service_names{msexch_service_reasonable_names},
     }},
    {"msexch_isclienttype"s,
     {
         .name_space{kWmiPathStd},
         .object_name{
             L"Win32_PerfRawData_MSExchangeISClientType_MSExchangeISClientType"},
         .service_names{msexch_service_reasonable_names},
     }},
    {"msexch_isstore"s,
     {
         .name_space{kWmiPathStd},
         .object_name{L"Win32_PerfRawData_MSExchangeISStore_MSExchangeISStore"},
         .service_names{msexch_service_reasonable_names},
     }},
    {"msexch_rpcclientaccess"s,
     {
         .name_space{kWmiPathStd},
         .object_name{
             L"Win32_PerfRawData_MSExchangeRpcClientAccess_MSExchangeRpcClientAccess"},
         .service_names{msexch_service_reasonable_names},
     }},
};

// Columns
const NamedWideStringVector g_section_columns = {

    {kOhm.data(),
     {
         L"Index",
         L"Name",
         L"Parent",
         L"SensorType",
         L"Value",
     }}};

const NamedStrVector g_section_subs = {

    {std::string{kWmiCpuLoad},
     {
         kSubSectionSystemPerf,
         kSubSectionComputerSystem,
     }},
    {std::string{kMsExch},
     {
         kMsExchActiveSync,
         kMsExchAvailability,
         kMsExchOwa,
         kMsExchAutoDiscovery,
         kMsExchIsClientType,
         kMsExchIsStore,
         kMsExchRpcClientAccess,
     }}};

WmiSource GetWmiSource(const std::string &uniq_name) {
    try {
        return g_section_objects.at(uniq_name);
    } catch (const std::out_of_range &) {
        XLOG::t.i("Section provider '{}' has no own WMI paths", uniq_name);
    }
    return {
        .name_space{L""},
        .object_name{L""},
        .service_names{},
    };
}
}  // namespace

SubSection::Type GetSubSectionType(std::string_view name) noexcept {
    return name == kMsExch ? SubSection::Type::full : SubSection::Type::sub;
}

std::string Wmi::makeBody() { return getData(); }

void WmiBase::setupByName() {
    auto src = GetWmiSource(uniq_name_);
    object_ = src.object_name;
    name_space_ = src.name_space;
    services_ = src.service_names;

    if (IsHeaderless(uniq_name_)) {
        setHeaderless();
    }

    try {
        columns_ = g_section_columns.at(uniq_name_);
    } catch (const std::out_of_range &) {
        XLOG::t.i("Column {} not found", uniq_name_);
    }

    try {
        const auto &subs = g_section_subs.at(uniq_name_);
        const auto type = GetSubSectionType(uniq_name_);
        for (const auto &sub : subs) {
            sub_objects_.emplace_back(sub, type);
        }
    } catch (const std::out_of_range &) {
        XLOG::t.i("Section {} not found", uniq_name_);
    }

    setupDelayOnFail();
}

/// Mid-level routine to build standard output WMI table.
/// Returns error code and string. String is empty if any error happens
/// String may be empty if not failed - this is important
/// WMI Timeout is NOT Error
/// #TODO Estimate optimization: do we need to reconnect to wrapper every time?
std::pair<std::string, wtools::WmiStatus> GenerateWmiTable(
    std::wstring_view wmi_namespace, const std::wstring &wmi_object,
    const std::vector<std::wstring> &columns_table,
    std::wstring_view separator) {
    if (wmi_object.empty() || wmi_namespace.empty()) {
        return {"", wtools::WmiStatus::bad_param};
    }

    const auto object_name = wtools::ToUtf8(wmi_object);
    tools::TimeLog tl(object_name);  // start measure
    const auto id = [&] {
        return fmt::format(R"("{}\{}")", wtools::ToUtf8(wmi_namespace),
                           object_name);
    };

    wtools::WmiWrapper wrapper;
    if (!wrapper.open()) {
        XLOG::l.e("WMI can't open '{}'", id());
        return {"", wtools::WmiStatus::fail_open};
    }

    if (!wrapper.connect(wmi_namespace)) {
        XLOG::l.e("WMI can't connect '{}'", id());
        return {"", wtools::WmiStatus::fail_connect};
    }

    if (!wrapper.impersonate()) {
        XLOG::l.e("WMI can't impersonate '{}'", id());
    }
    const auto &[ret, status] =
        wrapper.queryTable(columns_table, wmi_object, separator,
                           cfg::groups::g_global.getWmiTimeout());

    tl.writeLog(ret.size());

    return {wtools::ToUtf8(ret), status};
}

namespace {
std::wstring CharToWideString(char ch) {
    return wtools::ConvertToUtf16(std::string(1, ch));
}

bool IsAllAbsent(const std::vector<std::wstring> &services) {
    return rs::all_of(services, [](const auto &n) {
        return wtools::GetServiceStatus(n) == 0;
    });
}
}  // namespace

/// works in two modes
/// aggregated: object is absent, data are gathered from the subsections
/// standard: usual section, object must be present
std::string WmiBase::getData() {
    if (!services_.empty() && IsAllAbsent(services_)) {
        XLOG::t("Neither from required services '{}' has been installed",
                wtools::ToUtf8(tools::JoinVector(services_, L" ")));
        return {};
    }

    if (object_.empty()) {
        // special case for aggregating subs section into one
        std::string subs_out;
        for (auto &sub : sub_objects_) {
            XLOG::t("Sub section '{}'", sub.getUniqName());
            subs_out += sub.generateContent(subsection_mode_);
        }
        return subs_out;
    }

    XLOG::t.i("WMI main section '{}'", getUniqName());

    const auto sep = CharToWideString(separator());
    const auto &[data, status] =
        GenerateWmiTable(name_space_, object_, columns_, sep);

    // on timeout: reuse cache and ignore data, even if partially filled
    if (status == wtools::WmiStatus::timeout) {
        XLOG::d("On timeout in section '{}' try reuse cache", getUniqName());
        return WmiCachedDataHelper(cache_, {}, separator());
    }

    // on ok: update cache and send data as usually
    if (status == wtools::WmiStatus::ok) {
        if (data.empty()) {
            XLOG::t("Section '{}' has no more data", getUniqName());
            return {};
        }

        return WmiCachedDataHelper(cache_, data, separator());
    }

    // all other errors means disaster and we send NOTHING
    XLOG::l("Error reading WMI [{}] in '{}'", static_cast<int>(status),
            getUniqName());

    // to decrease annoyance level on monitoring site
    disableSectionTemporary();

    return {};
}

bool WmiBase::isAllowedByCurrentConfig() const {
    const auto name = getUniqName();

    if (!cfg::groups::g_global.allowedSection(name)) {
        XLOG::t("'{}' is skipped by config", name);
        return false;
    }

    // Wmi itself is allowed, we check conditions
    // 1. without sub section:
    if (sub_objects_.empty()) {
        return true;
    }

    // 2. with sub_section, check situation when parent
    // is allowed, but all sub  DISABLED DIRECTLY
    for (const auto &sub : sub_objects_) {
        if (!cfg::groups::g_global.isSectionDisabled(sub.getUniqName())) {
            return true;
        }
    }

    XLOG::d.t("'{}' and subs are skipped by config", name);
    return false;
}

void SubSection::setupByName() {
    auto src = GetWmiSource(uniq_name_);
    object_ = src.object_name;
    name_space_ = src.name_space;
}

std::string SubSection::makeBody() {
    const auto &[data, status] =
        GenerateWmiTable(name_space_, object_, {}, wmi::kSepString);

    // subsections ignore returned timeout
    if (status == wtools::WmiStatus::timeout) {
        XLOG::d("On timeout in sub section '{}' try reuse cache", uniq_name_);
        return WmiCachedDataHelper(cache_, {}, wmi::kSepChar);
    }

    if (status == wtools::WmiStatus::ok) {
        if (data.empty()) {
            XLOG::t("Sub Section '{}' has no more data", uniq_name_);
            return {};
        }
        return WmiCachedDataHelper(cache_, data, wmi::kSepChar);
    }

    // all other cases are rather not possible, still we want
    // to get information about error, caching is not allowed in
    // this case

    // this is ok if no wmi in the registry
    XLOG::d("Sub Section '{}' has no data to provide, status = [{}]",
            uniq_name_, static_cast<int>(status));
    return {};
}

std::string SubSection::generateContent(Mode mode) {
    try {
        auto section_body = makeBody();
        if (mode == Mode::standard && section_body.empty()) {
            return {};  // this may legal result
        }

        switch (type_) {
            case Type::full:
                return section::MakeHeader(uniq_name_, wmi::kSepChar) +
                       section_body;
            case Type::sub:
                return section::MakeSubSectionHeader(uniq_name_) + section_body;
        }
    } catch (const std::exception &e) {
        XLOG::l.crit(XLOG_FUNC + " Exception '{}' in '{}'", e, uniq_name_);
    }
    return {};
}
}  // namespace cma::provider
