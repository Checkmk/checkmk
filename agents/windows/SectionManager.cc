// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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

#include "SectionManager.h"
#include <unordered_map>
#include "Configuration.h"
#include "Environment.h"
#include "PerfCounterCommon.h"
#include "SectionCheckMK.h"
#include "SectionDF.h"
#include "SectionEventlog.h"
#include "SectionFileinfo.h"
#include "SectionGroup.h"
#include "SectionLogwatch.h"
#include "SectionMRPE.h"
#include "SectionMem.h"
#include "SectionOHM.h"
#include "SectionPS.h"
#include "SectionPluginGroup.h"
#include "SectionServices.h"
#include "SectionSkype.h"
#include "SectionSpool.h"
#include "SectionSystemtime.h"
#include "SectionUptime.h"
#include "SectionWMI.h"
#include "SectionWinperf.h"

namespace {
// Fix possible backwards incompatibility of section names by mapping
// 'old' names to 'new' ones.
std::string mapSectionName(const std::string &sectionName) {
    const std::unordered_map<std::string, std::string> mappedSectionNames = {
        {"webservices", "wmi_webservices"}, {"ohm", "openhardwaremonitor"}};
    const auto it = mappedSectionNames.find(sectionName);
    return it == mappedSectionNames.end() ? sectionName : it->second;
}

}  // namespace

template <>
winperf_counter from_string<winperf_counter>(const WinApiInterface &winapi,
                                             const std::string &value) {
    size_t colonIdx = value.find_last_of(":");
    if (colonIdx == std::string::npos) {
        std::cerr << "Invalid counter '" << value
                  << "' in section [winperf]: need number(or "
                     "text) and colon, e.g. 238:processor."
                  << std::endl;
        exit(1);
    }

    std::string name(value.begin() + colonIdx + 1, value.end());
    std::string base_id(value.begin(), value.begin() + colonIdx);
    auto non_digit = std::find_if_not(base_id.begin(), base_id.end(), isdigit);

    int id = 0;
    if (non_digit == base_id.end()) {
        id = std::stoi(base_id);
    } else {
        id = resolveCounterName(winapi, base_id);
        if (id == -1) {
            throw StringConversionError(
                "No matching performance counter id found for " + value);
        }
    }

    return {id, name};
}

SectionManager::SectionManager(Configuration &config,
                               OnlyFromConfigurable &only_from, Logger *logger,
                               const WinApiInterface &winapi)
    : _ps_use_wmi(config, "ps", "use_wmi", false, winapi)
    , _enabled_sections(config, "global", "sections", winapi, mapSectionName)
    , _disabled_sections(config, "global", "disabled_sections", winapi,
                         mapSectionName)
    , _realtime_sections(config, "global", "realtime_sections", winapi,
                         mapSectionName)
    , _script_local_includes(config, "local", "include", winapi)
    , _script_plugin_includes(config, "plugin", "include", winapi)
    , _winperf_counters(config, "winperf", "counters", winapi)
    , _env(config.getEnvironment())
    , _logger(logger)
    , _winapi(winapi) {
    loadStaticSections(config, only_from);
}

void SectionManager::emitConfigLoaded() {
    for (const auto &section : _sections) {
        section->postprocessConfig();
    }
}

void SectionManager::addSection(Section *section) {
    _sections.push_back(std::unique_ptr<Section>(section));
}

bool SectionManager::sectionEnabled(const std::string &name) const {
    // If no sections were set, assume they are all enabled
    std::string section_name = name;

    // Special handling for winperf_* custom sections
    if (name.substr(0, 8) == std::string("winperf_"))
        section_name = std::string("winperf");

    bool is_disabled =
        _disabled_sections->find(section_name) != _disabled_sections->end();

    bool is_enabled =
        !_enabled_sections.wasAssigned() ||
        (_enabled_sections->find(section_name) != _enabled_sections->end());
    return !is_disabled && is_enabled;
}

bool SectionManager::realtimeSectionEnabled(const std::string &name) const {
    return _realtime_sections->find(name) != _realtime_sections->end();
}

bool SectionManager::useRealtimeMonitoring() const {
    return _realtime_sections->size();
}

void SectionManager::loadDynamicSections() {
    for (const auto &counter : *_winperf_counters) {
        if (counter.id != -1) {
            addSection(
                (new SectionWinperf(counter.name, _env, _logger, _winapi))
                    ->withBase(counter.id));
        }
    }
}

void SectionManager::loadStaticSections(Configuration &config,
                                        OnlyFromConfigurable &only_from) {
    addSection(new SectionCheckMK(config, only_from, _script_statistics,
                                  _logger, _winapi));
    addSection(new SectionUptime(_env, _logger, _winapi));
    addSection(new SectionDF(_env, _logger, _winapi));
    addSection(new SectionPS(config, _logger, _winapi));
    addSection(new SectionMem(_env, _logger, _winapi));
    addSection(new SectionFileinfo(config, _logger, _winapi));
    addSection(new SectionServices(_env, _logger, _winapi));

    addSection(
        (new SectionWinperf("if", _env, _logger, _winapi))->withBase(510));
    addSection(
        (new SectionWinperf("phydisk", _env, _logger, _winapi))->withBase(234));
    addSection((new SectionWinperf("processor", _env, _logger, _winapi))
                   ->withBase(238));

    addSection(new SectionEventlog(config, _logger, _winapi));
    addSection(new SectionLogwatch(config, _logger, _winapi));

    addSection((new SectionWMI("dotnet_clrmemory", "dotnet_clrmemory", _env,
                               _logger, _winapi))
                   ->withObject(L"Win32_PerfRawData_NETFramework_NETCLRMemory")
                   ->withToggleIfMissing());

    addSection((new SectionGroup("wmi_cpuload", "wmi_cpuload", _env, _logger,
                                 _winapi, true))
                   ->withToggleIfMissing()
                   ->withSubSection(
                       (new SectionWMI("system_perf", "system_perf", _env,
                                       _logger, _winapi, true))
                           ->withObject(L"Win32_PerfRawData_PerfOS_System"))
                   ->withSubSection(
                       (new SectionWMI("computer_system", "computer_system",
                                       _env, _logger, _winapi, true))
                           ->withObject(L"Win32_ComputerSystem")));

    addSection(
        (new SectionGroup("msexch", "msexch", _env, _logger, _winapi, false))
            ->withToggleIfMissing()
            ->withSubSection(
                (new SectionWMI("msexch_activesync", "msexch_activesync", _env,
                                _logger, _winapi))
                    ->withObject(
                        L"Win32_PerfRawData_MSExchangeActiveSync_MSExchangeActiveSync"))
            ->withSubSection(
                (new SectionWMI("msexch_availability", "msexch_availability",
                                _env, _logger, _winapi))
                    ->withObject(
                        L"Win32_PerfRawData_MSExchangeAvailabilityService_MSExchangeAvailabilityService"))
            ->withSubSection(
                (new SectionWMI("msexch_owa", "msexch_owa", _env, _logger,
                                _winapi))
                    ->withObject(
                        L"Win32_PerfRawData_MSExchangeOWA_MSExchangeOWA"))
            ->withSubSection(
                (new SectionWMI("msexch_autodiscovery", "msexch_autodiscovery",
                                _env, _logger, _winapi))
                    ->withObject(
                        L"Win32_PerfRawData_MSExchangeAutodiscover_MSExchangeAutodiscover"))
            ->withSubSection(
                (new SectionWMI("msexch_isclienttype", "msexch_isclienttype",
                                _env, _logger, _winapi))
                    ->withObject(
                        L"Win32_PerfRawData_MSExchangeISClientType_MSExchangeISClientType"))
            ->withSubSection(
                (new SectionWMI("msexch_isstore", "msexch_isstore", _env,
                                _logger, _winapi))
                    ->withObject(
                        L"Win32_PerfRawData_MSExchangeISStore_MSExchangeISStore"))
            ->withSubSection(
                (new SectionWMI("msexch_rpcclientaccess",
                                "msexch_rpcclientaccess", _env, _logger,
                                _winapi))
                    ->withObject(
                        L"Win32_PerfRawData_MSExchangeRpcClientAccess_MSExchangeRpcClientAccess")));

    addSection(new SectionSkype(_env, _logger, _winapi));

    addSection((new SectionWMI("wmi_webservices", "wmi_webservices", _env,
                               _logger, _winapi))
                   ->withObject(L"Win32_PerfRawData_W3SVC_WebService")
                   ->withToggleIfMissing());

    addSection((new SectionOHM(config, _logger, _winapi))
                   ->withColumns({L"Index", L"Name", L"Parent", L"SensorType",
                                  L"Value"}));

    addSection(new SectionPluginGroup(config, _env.localDirectory(),
                                      script_type::LOCAL, _script_statistics,
                                      _logger, _winapi));
    for (const auto &[user, path] : *_script_local_includes) {
        addSection(new SectionPluginGroup(config, path, script_type::LOCAL,
                                          _script_statistics, _logger, _winapi,
                                          user));
    }

    addSection(new SectionPluginGroup(config, _env.pluginsDirectory(),
                                      script_type::PLUGIN, _script_statistics,
                                      _logger, _winapi));
    for (const auto &[user, path] : *_script_plugin_includes) {
        addSection(new SectionPluginGroup(config, path, script_type::PLUGIN,
                                          _script_statistics, _logger, _winapi,
                                          user));
    }

    addSection(new SectionSpool(_env, _logger, _winapi));
    addSection(new SectionMRPE(config, _logger, _winapi));

    addSection(new SectionSystemtime(_env, _logger, _winapi));
}
