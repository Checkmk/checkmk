// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/wmi.h"

#include <chrono>
#include <iostream>
#include <string>
#include <unordered_map>

#include "cfg.h"
#include "common/cfg_info.h"
#include "tools/_raii.h"

// controls behavior, we may want in the future,  works with older servers
// normally always true
constexpr bool g_add_wmi_status_column = true;

namespace cma::provider {

// use cache if body is empty(typical for new client, which returns empty on
// timeout) post process result
// update cache if data ok(not empty)
std::string WmiCachedDataHelper(std::string& cache_data,
                                const std::string& wmi_data, char separator) {
    // for very old servers
    if (!g_add_wmi_status_column) return wmi_data;

    if (!wmi_data.empty()) {
        // return original data with added OK in right column
        cache_data = wmi_data;  // store
        return wtools::WmiPostProcess(wmi_data, wtools::StatusColumn::ok,
                                      separator);
    }

    // we try to return cache with added "timeout" in last column
    if (!cache_data.empty())
        return wtools::WmiPostProcess(cache_data, wtools::StatusColumn::timeout,
                                      separator);

    XLOG::d.t(XLOG_FUNC + " no data to provide, cache is also empty");
    return {};
}

// ["Name", [Value1,Value2,...] ]
// ["msexch", [msexch_shit1, msexch_shit2] ] <-example
using NamedWideStringVector =
    std::unordered_map<std::string, std::vector<std::wstring>>;

using NamedStringVector =
    std::unordered_map<std::string, std::vector<std::string>>;

// pair from the "Connect point" and "Object"
// for example "Root\\Cimv2" and "Win32_PerfRawData_W3SVC_WebService"
using WmiSource = std::pair<std::wstring, std::wstring>;

// Link section name and WmiSource
using NamedWmiSources = std::unordered_map<std::string, WmiSource>;

// we configure our provider using static table with strings
// NOTHING MORE. ZERO OF PROGRAMMING

NamedWmiSources g_section_objects = {
    // start

    //
    {kDotNetClrMemory,  //
     {kWmiPathStd, L"Win32_PerfRawData_NETFramework_NETCLRMemory"}},

    //
    {kWmiWebservices,  //
     {kWmiPathStd, L"Win32_PerfRawData_W3SVC_WebService"}},

    //
    {kOhm,  //
     {kWmiPathOhm, L"Sensor"}},

    {kBadWmi,  // used for a testing or may be used as a template for other WMI
               // calls
     {L"Root\\BadWmiPath", L"BadSensor"}},

    // WMI CPULOAD group
    {"system_perf",  //
     {kWmiPathStd, L"Win32_PerfRawData_PerfOS_System"}},

    {"computer_system",  //
     {kWmiPathStd, L"Win32_ComputerSystem"}},

    {"msexch_activesync",
     {kWmiPathStd,
      L"Win32_PerfRawData_MSExchangeActiveSync_MSExchangeActiveSync"}},

    // MSEXCHANGE group
    {"msexch_availability",
     {kWmiPathStd,
      L"Win32_PerfRawData_MSExchangeAvailabilityService_MSExchangeAvailabilityService"}},

    {"msexch_owa",  //
     {kWmiPathStd, L"Win32_PerfRawData_MSExchangeOWA_MSExchangeOWA"}},

    {"msexch_autodiscovery",
     {kWmiPathStd,
      L"Win32_PerfRawData_MSExchangeAutodiscover_MSExchangeAutodiscover"}},

    {"msexch_isclienttype",
     {kWmiPathStd,
      L"Win32_PerfRawData_MSExchangeISClientType_MSExchangeISClientType"}},

    {"msexch_isstore",
     {kWmiPathStd, L"Win32_PerfRawData_MSExchangeISStore_MSExchangeISStore"}},

    {"msexch_rpcclientaccess",
     {kWmiPathStd,
      L"Win32_PerfRawData_MSExchangeRpcClientAccess_MSExchangeRpcClientAccess"}}

    // end
};

// Columns
NamedWideStringVector g_section_columns = {
    // start
    {kOhm,  //
     {L"Index", L"Name", L"Parent", L"SensorType", L"Value"}}
    // end
};

NamedStringVector g_section_subs = {
    // start
    {kWmiCpuLoad,  //
     {kSubSectionSystemPerf, kSubSectionComputerSystem}},
    {kMsExch,                //
     {kMsExchActiveSync,     //
      kMsExchAvailability,   //
      kMsExchOwa,            //
      kMsExchAutoDiscovery,  //
      kMsExchIsClientType,   //
      kMsExchIsStore,        //
      kMsExchRpcClientAccess}}
    // end
};

SubSection::Type GetSubSectionType(std::string_view name) noexcept {
    return name == kMsExch ? SubSection::Type::full : SubSection::Type::sub;
}

bool IsHeaderless(std::string_view name) noexcept { return name == kMsExch; }

void Wmi::setupByName() {
    try {
        auto& x = g_section_objects[uniq_name_];
        name_space_ = x.first;
        object_ = x.second;
    } catch (const std::exception& e) {
        // section not described in data
        XLOG::l.crit(
            "Invalid Name of the section provider '{}'. Exception: '{}'",
            uniq_name_, e.what());
        object_ = L"";
        name_space_ = L"";
        return;
    }

    if (IsHeaderless(uniq_name_)) {
        setHeaderless();
    }

    try {
        auto& x = g_section_columns[uniq_name_];
        columns_ = x;
    } catch (const std::exception&) {
        // ignoring this exception fully:
        // we do not care when object not found in the map
    }

    try {
        auto& subs = g_section_subs[uniq_name_];
        auto type = GetSubSectionType(uniq_name_);
        for (auto& sub : subs) {
            sub_objects_.emplace_back(SubSection(sub, type));
        }
    } catch (const std::exception&) {
        // ignoring this exception fully:
        // we do not care when object not found in the map
    }

    setupDelayOnFail();
}

// Intermediate routine to build standard output WMI table
// returns error code and string. String is empty if any error happens
// String may be empty if not failed - this is important
// WMI Timeout is NOT Error
// #TODO Estimate optimization: do we really need to reconnect to wrapper every
// time?
std::pair<std::string, wtools::WmiStatus> GenerateWmiTable(
    const std::wstring& wmi_namespace, const std::wstring& wmi_object,
    const std::vector<std::wstring>& columns_table,
    std::wstring_view separator) {
    using wtools::WmiStatus;

    if (wmi_object.empty() || wmi_namespace.empty()) {
        return {"", WmiStatus::bad_param};
    }

    auto object_name = wtools::ToUtf8(wmi_object);
    cma::tools::TimeLog tl(object_name);  // start measure
    auto id = [ wmi_namespace, object_name ]() -> auto {
        return fmt::formatv(R"("{}\{}")",                   //
                            wtools::ToUtf8(wmi_namespace),  //
                            object_name);
    };

    wtools::WmiWrapper wrapper;
    if (!wrapper.open()) {
        XLOG::l.e("WMI can't open '{}'", id());
        return {"", WmiStatus::fail_open};
    }

    if (!wrapper.connect(wmi_namespace)) {
        XLOG::l.e("WMI can't connect '{}'", id());
        return {"", WmiStatus::fail_connect};
    }

    if (!wrapper.impersonate()) {
        XLOG::l.e("WMI can't impersonate '{}'", id());
    }
    auto [ret, status] =
        wrapper.queryTable(columns_table, wmi_object, separator);

    tl.writeLog(ret.size());

    return {wtools::ToUtf8(ret), status};
}

static std::wstring CharToWideString(char ch) {
    std::wstring sep;
    sep += static_cast<wchar_t>(ch);

    return sep;
}

// works in two modes
// aggregated: object is absent, data are gathered from the subsections
// standard: usual section, object must be present
std::string Wmi::makeBody() {
    if (object_.empty()) {
        // special case for aggregating subs section into one
        std::string subs_out;
        for (auto& sub : sub_objects_) {
            XLOG::t("Sub section '{}'", sub.getUniqName());
            subs_out += sub.generateContent(subsection_mode_);
        }
        return subs_out;
    }

    XLOG::t.i("WMI main section '{}'", getUniqName());

    auto sep = CharToWideString(separator());
    auto [data, status] = GenerateWmiTable(name_space_, object_, columns_, sep);

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

    // all other errors means disaster and we sends NOTHING
    XLOG::l("Error reading WMI [{}] in '{}'", static_cast<int>(status),
            getUniqName());

    // to decrease annoyance level on monitoring site
    disableSectionTemporary();

    return {};
}

// [+] gtest
bool Wmi::isAllowedByCurrentConfig() const {
    auto name = getUniqName();

    auto allowed = cfg::groups::global.allowedSection(name);
    if (!allowed) {
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
    for (const auto& sub : sub_objects_) {
        auto sub_name = sub.getUniqName();

        if (!cfg::groups::global.isSectionDisabled(sub_name)) {
            return true;
        }
    }

    XLOG::d.t("'{}' and subs are skipped by config", name);
    return false;
}

// ****************************
// SubSection
// ****************************

void SubSection::setupByName() {
    try {
        auto& x = g_section_objects[uniq_name_];
        name_space_ = x.first;
        object_ = x.second;
    } catch (const std::exception& e) {
        XLOG::l.crit("Invalid Name of the sub section '{}'. Exception: '{}'",
                     uniq_name_, e.what());
        object_ = L"";
        name_space_ = L"";
        return;
    }
}

std::string SubSection::makeBody() {
    auto [data, status] =
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
    {
        // this is ok if no wmi in the registry
        XLOG::d("Sub Section '{}' has no data to provide, status = [{}]",
                uniq_name_, static_cast<int>(status));
        return {};
    }
}

std::string SubSection::generateContent(Mode mode) {
    // print body
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
    } catch (const std::exception& e) {
        XLOG::l.crit(XLOG_FUNC + " Exception '{}' in '{}'", e.what(),
                     uniq_name_);
    } catch (...) {
        XLOG::l.crit(XLOG_FUNC + " Exception UNKNOWN in '{}'", uniq_name_);
    }
    return {};
}

};  // namespace cma::provider
