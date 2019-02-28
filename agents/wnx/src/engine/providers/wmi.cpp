
// provides basic api to start and stop service
// IMPORTANT INFO for DEVs!
// WMI class is data-driven.

#include "stdafx.h"

#include <chrono>
#include <iostream>
#include <string>
#include <unordered_map>

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "common/cfg_info.h"

#include "cfg.h"

#include "providers/wmi.h"

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

NamedWmiSources G_SectionObjects = {
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

    // WMI CPULOAD group
    {"system_perf",  //
     {kWmiPathStd, L"Win32_PerfRawData_PerfOS_System"}},

    {"computer_system",  //
     {kWmiPathStd, L"Win32_ComputerSystem"}},

    {"msexch_activesync",
     {kWmiPathStd,
      L"Win32_PerfRawDara_MSExchangeActiveSync_MSExchangeActiveSync"}},

    // MSEXCHANGE group
    {"msexch_availability",
     {kWmiPathStd,
      L"Win32_PerfRawDara_MSExchangeAvailabilityService_MSExchangeAvailabilityService"}},

    {"msexch_owa",  //
     {kWmiPathStd, L"Win32_PerfRawDara_MSExchangeOWA_MSExchangeOWA"}},

    {"msexch_autodiscovery",
     {kWmiPathStd,
      L"Win32_PerfRawDara_MSExchangeAutodiscover_MSExchangeAutodiscover"}},

    {"msexch_isclienttype",
     {kWmiPathStd,
      L"Win32_PerfRawDara_MSExchangeISClientType_MSExchangeISClientType"}},

    {"msexch_isstore",
     {kWmiPathStd, L"Win32_PerfRawDara_MSExchangeISStore_MSExchangeISStore"}},

    {"msexch_rpcclientaccess",
     {kWmiPathStd,
      L"Win32_PerfRawDara_MSExchangeRpcClientAccess_MSExchangeRpcClientAccess"}}

    // end
};

// Columns
NamedWideStringVector G_SectionColumns = {
    // start
    {kOhm,  //
     {L"Index", L"Name", L"Parent", L"SensorType", L"Value"}}
    // end
};

NamedStringVector G_SectionSubs = {
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

// #TODO: confirm values, now 3600 seconds
// #TODO test it
std::unordered_map<std::string, std::chrono::duration<int>> G_DelaysOnFail = {
    {kDotNetClrMemory, cma::cfg::G_DefaultDelayOnFail},  //
    {kWmiWebservices, cma::cfg::G_DefaultDelayOnFail},   //
    {kWmiCpuLoad, cma::cfg::G_DefaultDelayOnFail},       //
    {kMsExch, cma::cfg::G_DefaultDelayOnFail}            //
};

void Wmi::setupByName() {
    // setup namespace and object
    try {
        auto& x = G_SectionObjects[uniq_name_];
        name_space_ = x.first;
        object_ = x.second;
    } catch (const std::exception& e) {
        // section not described in data
        XLOG::l(XLOG::kCritError)(
            "Invalid Name of the section provider {}. Exception: {}",
            uniq_name_, e.what());
        object_ = L"";
        name_space_ = L"";
        return;
    }

    // setup columns if any
    try {
        auto& x = G_SectionColumns[uniq_name_];
        columns_ = x;
    } catch (const std::exception&) {
        // ignoring this exception fully:
        // we do not care when object not found in the map
    }

    // setup columns if any
    try {
        auto& subs = G_SectionSubs[uniq_name_];
        for (auto& sub : subs) {
            sub_objects_.emplace_back(sub);
        }
    } catch (const std::exception&) {
        // ignoring this exception fully:
        // we do not care when object not found in the map
    }

    // setup delay on fail
    try {
        const auto& delay_in_seconds = G_DelaysOnFail[uniq_name_];
        delay_on_fail_ = delay_in_seconds;
    } catch (const std::exception&) {
        // do nothing here
    }
}

// intermediate routine to build standard output table
// tested internally
// returns empty string when failed
// #TODO Estimate as a part of official API
// #TODO Estimate optimization: do we really need to reconnect to wrapper every
// time?
std::string GenerateTable(const std::wstring NameSpace,
                          const std::wstring Object,
                          const std::vector<std::wstring> Columns) {
    using namespace wtools;
    if (Object.empty()) return "";

    auto id = [ NameSpace, Object ]() -> auto {
        return fmt::formatv("\"{}\\{}\"",              //
                            ConvertToUTF8(NameSpace),  //
                            ConvertToUTF8(Object));
    };

    wtools::WmiWrapper wrapper;
    if (!wrapper.open()) {
        XLOG::l.e(XLOG_FUNC + "Can't open {}", id());
        return {};
    }

    if (!wrapper.connect(NameSpace)) {
        XLOG::l.e(XLOG_FUNC + "Can't connect {}", id());
        return {};
    }

    if (!wrapper.impersonate()) {
        XLOG::l.e("XLOG_FUNC + Can't impersonate {}", id());
    }
    auto ret = wrapper.queryTable(Columns, Object);

    return ConvertToUTF8(ret);
}

// works in two modes
// aggregated: object is absent, data are gathered from the subsections
// standard: usual section, object must be present
std::string Wmi::makeBody() const {
    if (object_.empty()) {
        // special case for aggregating subs section into one
        std::string subs_out;
        for (auto& sub : sub_objects_) {
            XLOG::l.t("sub section {}", sub.getUniqName());
            subs_out += sub.generateContent();
        }
        return subs_out;
    }
    XLOG::l.t("main section {}", getUniqName());
    return GenerateTable(name_space_, object_, columns_);
}

// gtest is not easy here, #TODO rethink how test this
bool Wmi::isAllowedByCurrentConfig() const {
    using namespace cma::cfg;

    // check Wmi itself
    auto name = getUniqName();
    bool allowed = groups::global.allowedSection(name);
    if (!allowed) {
        XLOG::l.t("{} is skipped by config", name);
        return false;
    }

    // Wmi itself is allowed, we check conditions
    // 1. without sub section:
    if (sub_objects_.size() == 0) return true;

    // 2. with sub_section, check situation when parent
    // is allowed, but all sub  DISABLED DIRECTLY
    for (auto& sub : sub_objects_) {
        auto sub_name = sub.getUniqName();

        if (!groups::global.isSectionDisabled(sub_name)) return true;
    }

    XLOG::l.t("{} and subs are skipped by config", name);
    return false;
}

// ****************************
// SubSection
// ****************************

void SubSection::setupByName() {
    // setup namespace and object
    try {
        auto& x = G_SectionObjects[uniq_name_];
        name_space_ = x.first;
        object_ = x.second;
    } catch (const std::exception& e) {
        // section not described in data
        // BUT MUST BE, this is developers error
        XLOG::l.crit("Invalid Name of the sub section {}. Exception: {}",
                     uniq_name_, e.what());
        object_ = L"";
        name_space_ = L"";
        return;
    }
}

std::string SubSection::makeBody() const {
    return GenerateTable(name_space_, object_, {});
}

std::string SubSection::generateContent() const {
    // print body
    auto section_body = makeBody();
    try {
        if (section_body.empty()) {
            // this is not normal usually
            XLOG::d("SubSection {} cannot provide data", uniq_name_);
            return {};
        } else {
            // print header with default or commanded section name
            return std::move(section::MakeSubSectionHeader(uniq_name_) +
                             section_body);
        }
    } catch (const std::exception& e) {
        XLOG::l.crit("Exception {} in {}", e.what(), uniq_name_);
    } catch (...) {
        XLOG::l.crit("Exception UNKNOWN in {}", uniq_name_);
    }
    return {};
}

}  // namespace provider
};  // namespace cma
