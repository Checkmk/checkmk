
// provides basic api to start and stop service
// IMPORTANT INFO for DEVs!
// WMI class is data-driven.

#include "stdafx.h"

#include "providers/wmi.h"

#include <chrono>
#include <iostream>
#include <string>
#include <unordered_map>

#include "cfg.h"
#include "common/cfg_info.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma {

namespace provider {

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

    {kBadWmi,  // used for a testing or may be used as a template for other WMI calls
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
    {kMsExch,                  //
     {"msexch_activesync",     //
      "msexch_availability",   //
      "msexch_owa",            //
      "msexch_autodiscovery",  //
      "msexch_isclienttype",   //
      "msexch_isstore",        //
      "msexch_rpcclientaccess"}}
    // end
};

// This is allowed.
using namespace std::chrono;

void Wmi::setupByName() {
    // setup namespace and object
    try {
        auto& x = g_section_objects[uniq_name_];
        name_space_ = x.first;
        object_ = x.second;
    } catch (const std::exception& e) {
        // section not described in data
        XLOG::l(XLOG::kCritError)(
            "Invalid Name of the section provider '{}'. Exception: '{}'",
            uniq_name_, e.what());
        object_ = L"";
        name_space_ = L"";
        return;
    }

    // setup columns if any
    try {
        auto& x = g_section_columns[uniq_name_];
        columns_ = x;
    } catch (const std::exception&) {
        // ignoring this exception fully:
        // we do not care when object not found in the map
    }

    // setup columns if any
    try {
        auto& subs = g_section_subs[uniq_name_];
        for (auto& sub : subs) {
            sub_objects_.emplace_back(sub);
        }
    } catch (const std::exception&) {
        // ignoring this exception fully:
        // we do not care when object not found in the map
    }

    setupDelayOnFail();
}

// Intermediate routine to build standard output WMI table
// returns error code and string. String is empty if failed
// String may be empty if not failed - this is important
// WMI Timeout is NOT Error
// #TODO Estimate optimization: do we really need to reconnect to wrapper every
// time?
std::pair<WmiStatus, std::string> GenerateWmiTable(
    const std::wstring& wmi_namespace, const std::wstring& wmi_object,
    const std::vector<std::wstring> columns_table) {
    using namespace wtools;

    if (wmi_object.empty() || wmi_namespace.empty())
        return {WmiStatus::bad_param, ""};

    auto object_name = ConvertToUTF8(wmi_object);
    cma::tools::TimeLog tl(object_name);  // start measure
    auto id = [ wmi_namespace, object_name ]() -> auto {
        return fmt::formatv(R"("{}\{}")",                  //
                            ConvertToUTF8(wmi_namespace),  //
                            object_name);
    };

    wtools::WmiWrapper wrapper;
    if (!wrapper.open()) {
        XLOG::l.e(XLOG_FUNC + "Can't open {}", id());
        return {WmiStatus::fail_open, ""};
    }

    if (!wrapper.connect(wmi_namespace)) {
        XLOG::l.e(XLOG_FUNC + "Can't connect {}", id());
        return {WmiStatus::fail_connect, ""};
    }

    if (!wrapper.impersonate()) {
        XLOG::l.e("XLOG_FUNC + Can't impersonate {}", id());
    }
    auto ret = wrapper.queryTable(columns_table, wmi_object);

    tl.writeLog(ret.size());  // fix measure

    return {WmiStatus::ok, ConvertToUTF8(ret)};
}

// works in two modes
// aggregated: object is absent, data are gathered from the subsections
// standard: usual section, object must be present
std::string Wmi::makeBody() {
    if (object_.empty()) {
        // special case for aggregating subs section into one
        std::string subs_out;
        for (auto& sub : sub_objects_) {
            XLOG::l.t("sub section '{}'", sub.getUniqName());
            subs_out += sub.generateContent();
        }
        return subs_out;
    }
    XLOG::l.i("main section '{}'", getUniqName());
    auto [err, data] = GenerateWmiTable(name_space_, object_, columns_);

    // check error code, on error we could stop section sending
    if (err != WmiStatus::ok) disableSectionTemporary();

    return data;
}

// [+] gtest
bool Wmi::isAllowedByCurrentConfig() const {
    using namespace cma::cfg;

    // check Wmi itself
    auto name = getUniqName();
    bool allowed = groups::global.allowedSection(name);
    if (!allowed) {
        XLOG::l.t("'{}' is skipped by config", name);
        return false;
    }

    // Wmi itself is allowed, we check conditions
    // 1. without sub section:
    if (sub_objects_.empty()) return true;

    // 2. with sub_section, check situation when parent
    // is allowed, but all sub  DISABLED DIRECTLY
    for (auto& sub : sub_objects_) {
        auto sub_name = sub.getUniqName();

        if (!groups::global.isSectionDisabled(sub_name)) return true;
    }

    XLOG::l.t("'{}' and subs are skipped by config", name);
    return false;
}

// ****************************
// SubSection
// ****************************

void SubSection::setupByName() {
    // setup namespace and object
    try {
        auto& x = g_section_objects[uniq_name_];
        name_space_ = x.first;
        object_ = x.second;
    } catch (const std::exception& e) {
        // section not described in data
        // BUT MUST BE, this is developers error
        XLOG::l.crit("Invalid Name of the sub section '{}'. Exception: '{}'",
                     uniq_name_, e.what());
        object_ = L"";
        name_space_ = L"";
        return;
    }
}

std::string SubSection::makeBody() {
    auto [err, data] = GenerateWmiTable(name_space_, object_, {});
    // subsections ignore returned error
    return data;
}

std::string SubSection::generateContent() {
    // print body
    auto section_body = makeBody();
    try {
        if (section_body.empty()) {
            // this is not normal usually
            XLOG::d("SubSection '{}' cannot provide data", uniq_name_);
            return {};
        }

        // print header with default or commanded section name
        return std::move(section::MakeSubSectionHeader(uniq_name_) +
                         section_body);

    } catch (const std::exception& e) {
        XLOG::l.crit(XLOG_FUNC + " Exception '{}' in '{}'", e.what(),
                     uniq_name_);
    } catch (...) {
        XLOG::l.crit(XLOG_FUNC + " Exception UNKNOWN in '{}'", uniq_name_);
    }
    return {};
}

}  // namespace provider
};  // namespace cma
