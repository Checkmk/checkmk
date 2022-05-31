// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Configuration Parameters for YAML and YAML-INI related configs
#pragma once
#include <cstdint>
#include <string_view>

namespace cma::cfg {

namespace yml_var {
constexpr const std::string_view kBuiltinPlugins = "$BUILTIN_PLUGINS_PATH$";
constexpr const std::string_view kCore = "$BUILTIN_AGENT_PATH$";
constexpr const std::string_view kLocal = "$CUSTOM_LOCAL_PATH$ ";
constexpr const std::string_view kUserPlugins = "$CUSTOM_PLUGINS_PATH$";
constexpr const std::string_view kAgent = "$CUSTOM_AGENT_PATH$";

constexpr const std::string_view kBuiltinOld = "@builtin";
constexpr const std::string_view kCoreOld = "@core";
constexpr const std::string_view kLocalOld = "@local";
constexpr const std::string_view kUserOld = "@user";
constexpr const std::string_view kDataOld = "@data";

};  // namespace yml_var

namespace groups {
constexpr std::string_view kGlobal = "global";
constexpr std::string_view kWinPerf = "winperf";
constexpr std::string_view kLogFiles = "logfiles";
constexpr std::string_view kPs = "ps";
constexpr std::string_view kPlugins = "plugins";
constexpr std::string_view kFileInfo = "fileinfo";
constexpr std::string_view kMrpe = "mrpe";
constexpr std::string_view kLogWatchEvent = "logwatch";
constexpr std::string_view kLocal = "local";
constexpr std::string_view kSystem = "system";
constexpr std::string_view kModules = "modules";
}  // namespace groups

// ALL name of variables in the YAML
namespace vars {
// universal
constexpr std::string_view kEnabled = "enabled";  // bool
constexpr std::string_view kFile = "file";        // string
constexpr std::string_view kTimeout = "timeout";  // int

// group "global"
const char *const kInstall = "install";                               // bool
const char *const kName = "name";                                     // string
const char *const kPort = "port";                                     // int
const char *const kOnlyFrom = "only_from";                            // seq
const char *const kIpv6 = "ipv6";                                     // bool
const char *const kExecute = "execute";                               // seq
const char *const kHost = "host";                                     // seq
const char *const kAsync = "async";                                   // bool
const char *const kTryKillPluginProcess = "try_kill_plugin_process";  // string
const char *const kSectionFlush = "section_flush";                    // bool
const char *const kGlobalEncrypt = "encrypted";                       // bool
const char *const kGlobalPassword = "passphrase";                     // string
const char *const kGlobalWmiTimeout = "wmi_timeout";                  // int
const std::string_view kCpuLoadMethod{"cpuload_method"};              // string

const char *const kGlobalRemoveLegacy = "remove_legacy";  // bool

const char *const kRealTime = "realtime";    // map
const char *const kRtTimeout = "timeout";    // int
const char *const kRtPort = "port";          // int
const char *const kRtEncrypt = "encrypted";  // bool
const char *const kRtRun = "run";            // seq
const char *const kRtEnabled = "enabled";    // bool

const char *const kSectionsEnabled = "sections";            // seq
const char *const kSectionsDisabled = "disabled_sections";  // seq

const char *const kLogging = "logging";       // map
const char *const kLogLocation = "location";  // bool
const char *const kLogDebug = "debug";        // string no, yes, all
const char *const kLogWinDbg = "windbg";      // bool
const char *const kLogEvent = "eventlog";     // bool
const char *const kLogFile = "file";          // string
const char *const kLogFileMaxFileCount = "max_file_count";  // string
const char *const kLogFileMaxFileSize = "max_file_size";    // string

// group plugins
const char *const kPluginsFolders = "folders";            // seq
const char *const kPluginsDefaultFolderMark = "default";  // seq
const char *const kPluginsExecution = "execution";        // seq
const char *const kPluginMaxWait = "max_wait";            // int
const char *const kPluginAsyncStart = "async_start";      // bool

// to be replaced
constexpr std::string_view kLocalUserFolder = yml_var::kLocal;
constexpr std::string_view kPluginUserFolder = yml_var::kUserPlugins;
constexpr std::string_view kPluginCoreFolder = yml_var::kCore;
constexpr std::string_view kPluginBuiltinFolder = yml_var::kBuiltinPlugins;
constexpr std::string_view kProgramDataFolder = yml_var::kAgent;

// plugins.execution
const char *const kPluginPattern = "pattern";     // string
const char *const kPluginTimeout = "timeout";     // int
const char *const kPluginAsync = "async";         // bool
const char *const kPluginRetry = "retry_count";   // int
const char *const kPluginCacheAge = "cache_age";  // int
const char *const kPluginExe = "exe";             // string
const char *const kPluginRun = "run";             // bool

const char *const kPluginGroup = "group";  // string
const char *const kPluginUser = "user";    // string

// group "winperf"
// root
const char *const kWinPerfCounters = "counters";      // seq
const char *const kWinPerfExe = "exe";                // string
const char *const kWinPerfPrefixName = "prefix";      // string
const char *const kWinPerfPrefixDefault = "winperf";  // string
const char *const kWinPerfTimeout = "timeout";        // int
const char *const kWinPerfTrace = "trace";            // bool
const char *const kWinPerfFork = "fork";              // bool

// group "logwatch"
// root
const char *const kLogWatchEventSendall = "sendall";                // bool
const char *const kLogWatchEventVistaApi = "vista_api";             // bool
const char *const kLogWatchEventSkip = "skip_duplicated";           // bool
const char *const kLogWatchEventMaxSize = "max_size";               // int
const char *const kLogWatchEventMaxEntries = "max_entries";         // int
const char *const kLogWatchEventTimeout = "timeout";                // int
const char *const kLogWatchEventMaxLineLength = "max_line_length";  // int
const char *const kLogWatchEventLogFile = "logfile";                // string

// Key Words in logwatch.logfile section of the YAML config file
// example:
// logfile:
//   - 'Application' : warn
//                     ^^^^
constexpr const char *const kLogWatchEvent_ParamWords[] = {
    "ignore",  // 0
    "off",     // 1 default
    "all",     // 2
    "warn",    // 3
    "crit",    // 4
};

const char *const kLogWatchEvent_ParamDefault = kLogWatchEvent_ParamWords[1];

const char *const kLogWatchEvent_ContextWords[] = {
    "context",    // 0
    "nocontext",  // 1
};

// winperf.counters[].

// group "logfiles"
const char *const kLogFilesView = "view";  // seq

// logfiles.view[]. subgroup is array from:
const char *const kLogFilesObserve = "observe";          // string
const char *const kLogFilesName = "name";                // string
const char *const kLogFilesDescription = "description";  // string
const char *const kLogFilesRotated = "rotated";          // bool
const char *const kLogFilesContext = "context";          // bool
const char *const kLogFilesFromStart = "from_start";     // bool
const char *const kLogFilesPatterns = "patterns";        // map

// criteria logfiles.view.[index].patterns.
const char *const kLogFilesOk = "ok";          // string
const char *const kLogFilesCrit = "crit";      // string
const char *const kLogFilesWarn = "warn";      // string
const char *const kLogFilesIgnore = "ignore";  // string

const char *const kLogFilesConfig = "config";    // string
const char *const kLogFilesGlob = "glob";        // string
const char *const kLogFilesPattern = "pattern";  // string

// group "ps"
const char *const kPsUseWmi = "use_wmi";      // bool
const char *const kPsFullPath = "full_path";  // bool

// group "fileinfo"
const char *const kFileInfoPath = "path";  // sequence

// group "mrpe"
const char *const kMrpeConfig = "config";      // sequence
const char *const kMrpeParallel = "parallel";  // boool

// group "modules"
constexpr std::string_view kModulesTable = "table";  // list of nodes
constexpr std::string_view kModulesName = "name";    // string
constexpr std::string_view kModulesExts = "exts";    // list of string
constexpr std::string_view kModulesExec = "exec";    // string
constexpr std::string_view kModulesDir = "dir";      // string

constexpr std::string_view kModulesPython = "python";  // string
constexpr std::string_view kModulesQuickReinstall = "quick_reinstall";  // bool

// group "system"
constexpr std::string_view kController = "controller";  // dictionary
constexpr std::string_view kControllerRun = "run";      // bool
constexpr std::string_view kControllerCheck = "check";  // bool
constexpr std::string_view kControllerForceLegacy = "force_legacy";    // bool
constexpr std::string_view kControllerAgentChannel = "agent_channel";  // str
constexpr std::string_view kControllerLocalOnly = "local_only";        // bool
constexpr std::string_view kControllerOnCrash = "on_crash";            // string

constexpr const char *const kFirewall = "firewall";  // dictionary
constexpr const char *const kFirewallMode = "mode";  // string
constexpr const char *const kFirewallPort = "port";  // string

constexpr const char *const kCleanupUninstall = "cleanup_uninstall";  // string

constexpr const char *const kService = "service";                  // dictionary
constexpr const char *const kRestartOnCrash = "restart_on_crash";  // bool
constexpr const char *const kErrorMode = "error_mode";             // string
constexpr const char *const kStartMode = "start_mode";             // string

constexpr const char *const kWaitNetwork = "wait_network";  // int, seconds
}  // namespace vars

namespace values {

// global.cpuload_method
const std::string_view kCpuLoadWmi{"use_wmi"};
const std::string_view kCpuLoadPerf{"use_perf"};

// modules.table
constexpr std::string_view kModulesNamePython = "python-3";  //
constexpr std::string_view kModulesCmdPython =
    ".venv\\Scripts\\python.exe {}";  //

// modules...
constexpr std::string_view kModuleUsageSystem = "system";
constexpr std::string_view kModuleUsageAuto = "auto";

// Firewall.Mode
constexpr const char *const kModeConfigure = "configure";  // install [*]
constexpr const char *const kModeNone = "none";            // does noting
constexpr const char *const kModeRemove = "remove";        // remove

// Firewall.Port
constexpr const char *const kFirewallPortAll = "all";    // open all ports
constexpr const char *const kFirewallPortAuto = "auto";  // port in config, [*]

// CleanupUninstall
constexpr const char *const kCleanupNone = "none";    // delete nothing
constexpr const char *const kCleanupSmart = "smart";  // delete only owned [*]
constexpr const char *const kCleanupAll = "all";      // delete all

// service.start_mode
constexpr const char *const kStartModeAuto = "auto";        // start on boot
constexpr const char *const kStartModeDelayed = "delayed";  // start after boot
constexpr const char *const kStartModeDemand = "demand";    // start manually
constexpr const char *const kStartModeDisabled = "disabled";  // start disabled

constexpr const char *const kErrorModeIgnore = "ignore";  // do nothing
constexpr const char *const kErrorModeLog = "log";        // log situation

// global.try_kill_plugin_process
constexpr const char *const kTryKillSafe = "safe";  // only well known processes
constexpr const char *const kTryKillAll = "all";    // all plugins
constexpr const char *const kTryKillNo = "no";      //

// system.controlle.on_crash
constexpr std::string_view kControllerOnCrashIgnore{"ignore"};
constexpr std::string_view kControllerOnCrashEmergency{"emergency_mode"};

}  // namespace values

namespace defaults {
const std::string_view kCpuLoad{values::kCpuLoadPerf};
constexpr const char *const kStartMode = values::kStartModeAuto;
constexpr const char *const kErrorMode = values::kErrorModeLog;
constexpr bool kRestartOnCrash = true;
constexpr uint32_t kMrpeTimeout = 10;

constexpr const char *const kTryKillPluginProcess = values::kTryKillSafe;

constexpr std::string_view kModulesDir = "modules\\{}";

constexpr std::string_view kModuleUsageDefaultMode = values::kModuleUsageAuto;

constexpr uint32_t kServiceWaitNetwork = 30;
constexpr std::string_view kControllerAgentChannelDefault{"localhost:28250"};
constexpr std::string_view kControllerOnCrashDefault{
    values::kControllerOnCrashIgnore};
constexpr bool kControllerLocalOnly{true};
constexpr bool kControllerForceLegacy{false};
constexpr bool kControllerCheck{true};

}  // namespace defaults

}  // namespace cma::cfg
