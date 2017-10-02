#include "SectionManager.h"
#include <unordered_map>
#include "sections/SectionCheckMK.h"
#include "sections/SectionCrashDebug.h"
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

SectionManager::SectionManager(Configuration &config, const Environment &env)
    : _ps_use_wmi(config, "ps", "use_wmi", false)
    , _enabled_sections(config, "global", "sections", mapSectionName)
    , _disabled_sections(config, "global", "disabled_sections", mapSectionName)
    , _realtime_sections(config, "global", "realtime_sections", mapSectionName)
    , _script_local_includes(config, "local", "include")
    , _script_plugin_includes(config, "plugin", "include")
    , _winperf_counters(config, "winperf", "counters") {
    loadStaticSections(config, env);
}

void SectionManager::emitConfigLoaded(const Environment &env) {
    for (const auto &section : _sections) {
        section->postprocessConfig(env);
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
            addSection((new SectionWinperf(counter->name.c_str()))
                           ->withBase(counter->id));
        }
    }
}

void SectionManager::loadStaticSections(Configuration &config,
                                        const Environment &env) {
    addSection(new SectionCrashDebug(config));
    addSection(new SectionCheckMK(config, env));
    addSection(new SectionUptime());
    addSection((new SectionDF())->withRealtimeSupport());
    addSection(new SectionPS(config));
    addSection((new SectionMem())->withRealtimeSupport());
    addSection(new SectionFileinfo(config));
    addSection(new SectionServices());

    addSection((new SectionWinperf("if"))->withBase(510));
    addSection((new SectionWinperf("phydisk"))->withBase(234));
    addSection((new SectionWinperf("processor"))
                   ->withBase(238)
                   ->withRealtimeSupport());

    addSection(new SectionEventlog(config));
    addSection(new SectionLogwatch(config, env));

    addSection((new SectionWMI("dotnet_clrmemory"))
                   ->withObject(L"Win32_PerfRawData_NETFramework_NETCLRMemory")
                   ->withToggleIfMissing());

    addSection((new SectionGroup("wmi_cpuload"))
                   ->withToggleIfMissing()
                   ->withNestedSubtables()
                   ->withSubSection(
                       (new SectionWMI("system_perf"))
                           ->withObject(L"Win32_PerfRawData_PerfOS_System"))
                   ->withSubSection((new SectionWMI("computer_system"))
                                        ->withObject(L"Win32_ComputerSystem"))
                   ->withSeparator(','));

    addSection(
        (new SectionGroup("msexch"))
            ->withToggleIfMissing()
            ->withSubSection((new SectionWMI("msexch_activesync"))
                                 ->withObject(L"Win32_PerfRawData_MSExchangeActiveSync_MSExchangeActiveSync"))
            ->withSubSection((new SectionWMI("msexch_availability"))
                                 ->withObject(L"Win32_PerfRawData_MSExchangeAvailabilityService"))
            ->withSubSection(
                (new SectionWMI("msexch_owa"))->withObject(L"Win32_PerfRawData_MSExchangeOWA_MSExchangeOWA"))
            ->withSubSection((new SectionWMI("msexch_autodiscovery"))
                                 ->withObject(L"Win32_PerfRawData_MSExchangeAutodiscover_MSExchangeAutodiscover"))
            ->withSubSection((new SectionWMI("msexch_isclienttype"))
                                 ->withObject(L"Win32_PerfRawData_MSExchangeISClientType_MSExchangeISClientType"))
            ->withSubSection((new SectionWMI("msexch_isstore"))
                                 ->withObject(L"Win32_PerfRawData_MSExchangeISStore_MSExchangeISStore"))
            ->withSubSection((new SectionWMI("msexch_rpcclientaccess"))
                                 ->withObject(L"Win32_PerfRawData_MSExchangeRpcClientAccess_MSExchangeRpcClientAccess"))
            ->withHiddenHeader()
            ->withSeparator(','));

    addSection(new SectionSkype());

    addSection((new SectionWMI("wmi_webservices"))
                   ->withObject(L"Win32_PerfRawData_W3SVC_WebService")
                   ->withToggleIfMissing());

    addSection((new SectionOHM(config, env))
                   ->withColumns({L"Index", L"Name", L"Parent", L"SensorType",
                                  L"Value"}));

    addSection(new SectionPluginGroup(config, env.localDirectory(), LOCAL));
    for (const auto &include : *_script_local_includes) {
        addSection(new SectionPluginGroup(config, include.second, LOCAL,
                                          include.first));
    }

    addSection(new SectionPluginGroup(config, env.pluginsDirectory(), PLUGIN));
    for (const auto &include : *_script_plugin_includes) {
        addSection(new SectionPluginGroup(config, include.second, PLUGIN,
                                          include.first));
    }

    addSection(new SectionSpool());
    addSection(new SectionMRPE(config));

    addSection(new SectionSystemtime());
}
