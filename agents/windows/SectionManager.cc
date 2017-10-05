#include "SectionManager.h"
#include <unordered_map>
#include "Configuration.h"
#include "Environment.h"
#include "sections/SectionCheckMK.h"
#include "sections/SectionDF.h"
#include "sections/SectionEventlog.h"
#include "sections/SectionFileinfo.h"
#include "sections/SectionGroup.h"
#include "sections/SectionLogwatch.h"
#include "sections/SectionMRPE.h"
#include "sections/SectionMem.h"
#include "sections/SectionOHM.h"
#include "sections/SectionPS.h"
#include "sections/SectionPluginGroup.h"
#include "sections/SectionServices.h"
#include "sections/SectionSkype.h"
#include "sections/SectionSpool.h"
#include "sections/SectionSystemtime.h"
#include "sections/SectionUptime.h"
#include "sections/SectionWMI.h"
#include "sections/SectionWinperf.h"

namespace {
// Fix possible backwards incompatibility of section names by mapping
// 'old' names to 'new' ones.
std::string mapSectionName(const std::string &sectionName) {
    const std::unordered_map<std::string, std::string> mappedSectionNames = {
        {"webservices", "wmi_webservices"}};
    const auto it = mappedSectionNames.find(sectionName);
    return it == mappedSectionNames.end() ? sectionName : it->second;
}

}  // namespace

SectionManager::SectionManager(Configuration &config, Logger *logger,
                               const WinApiAdaptor &winapi)
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
    loadStaticSections(config);
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
    for (winperf_counter *counter : *_winperf_counters) {
        if (counter->id != -1) {
            addSection((new SectionWinperf(counter->name.c_str(), _env, _logger,
                                           _winapi))
                           ->withBase(counter->id));
        }
    }
}

void SectionManager::loadStaticSections(Configuration &config) {
    addSection(new SectionCheckMK(config, _logger, _winapi));
    addSection(new SectionUptime(_env, _logger, _winapi));
    addSection((new SectionDF(_env, _logger, _winapi))->withRealtimeSupport());
    addSection(new SectionPS(config, _logger, _winapi));
    addSection((new SectionMem(_env, _logger, _winapi))->withRealtimeSupport());
    addSection(new SectionFileinfo(config, _logger, _winapi));
    addSection(new SectionServices(_env, _logger, _winapi));

    addSection(
        (new SectionWinperf("if", _env, _logger, _winapi))->withBase(510));
    addSection(
        (new SectionWinperf("phydisk", _env, _logger, _winapi))->withBase(234));
    addSection((new SectionWinperf("processor", _env, _logger, _winapi))
                   ->withBase(238)
                   ->withRealtimeSupport());

    addSection(new SectionEventlog(config, _logger, _winapi));
    addSection(new SectionLogwatch(config, _logger, _winapi));

    addSection((new SectionWMI("dotnet_clrmemory", "dotnet_clrmemory", _env,
                               _logger, _winapi))
                   ->withObject(L"Win32_PerfRawData_NETFramework_NETCLRMemory")
                   ->withToggleIfMissing());

    addSection(
        (new SectionGroup("wmi_cpuload", "wmi_cpuload", _env, _logger, _winapi))
            ->withToggleIfMissing()
            ->withNestedSubtables()
            ->withSubSection(
                (new SectionWMI("system_perf", "system_perf", _env, _logger,
                                _winapi))
                    ->withObject(L"Win32_PerfRawData_PerfOS_System"))
            ->withSubSection(
                (new SectionWMI("computer_system", "computer_system", _env,
                                _logger, _winapi))
                    ->withObject(L"Win32_ComputerSystem"))
            ->withSeparator(','));

    addSection(
        (new SectionGroup("msexch", "msexch", _env, _logger, _winapi))
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
                        L"Win32_PerfRawData_MSExchangeAvailabilityService"))
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
                        L"Win32_PerfRawData_MSExchangeRpcClientAccess_MSExchangeRpcClientAccess"))
            ->withHiddenHeader()
            ->withSeparator(','));

    addSection(new SectionSkype(_env, _logger, _winapi));

    addSection((new SectionWMI("wmi_webservices", "wmi_webservices", _env,
                               _logger, _winapi))
                   ->withObject(L"Win32_PerfRawData_W3SVC_WebService")
                   ->withToggleIfMissing());

    addSection((new SectionOHM(config, _logger, _winapi))
                   ->withColumns({L"Index", L"Name", L"Parent", L"SensorType",
                                  L"Value"}));

    addSection(new SectionPluginGroup(config, _env.localDirectory(), LOCAL,
                                      _logger, _winapi));
    for (const auto &include : *_script_local_includes) {
        addSection(new SectionPluginGroup(config, include.second, LOCAL,
                                          _logger, _winapi, include.first));
    }

    addSection(new SectionPluginGroup(config, _env.pluginsDirectory(), PLUGIN,
                                      _logger, _winapi));
    for (const auto &include : *_script_plugin_includes) {
        addSection(new SectionPluginGroup(config, include.second, PLUGIN,
                                          _logger, _winapi, include.first));
    }

    addSection(new SectionSpool(_env, _logger, _winapi));
    addSection(new SectionMRPE(config, _logger, _winapi));

    addSection(new SectionSystemtime(_env, _logger, _winapi));
}
