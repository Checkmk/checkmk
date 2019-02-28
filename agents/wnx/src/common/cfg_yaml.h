// Configuration Parameters for YAML and YAML-INI related configs
#pragma once
namespace cma::cfg {

namespace groups {
constexpr const char* const kGlobal = "global";
constexpr const char* const kWinPerf = "winperf";
constexpr const char* const kLogFiles = "logfiles";
constexpr const char* const kPs = "ps";
constexpr const char* const kPlugins = "plugins";
constexpr const char* const kLocal = "local";
constexpr const char* const kFileInfo = "fileinfo";
constexpr const char* const kMrpe = "mrpe";
constexpr const char* const kLogWatchEvent = "logwatch";
constexpr const char* const kLocalGroup = "local";
}  // namespace groups

// ALL name of variables in the YAML
namespace vars {
// universal
const char* const kEnabled = "enabled";  // bool
const char* const kFile = "file";        // string
const char* const kTimeout = "timeout";  // int

// group "global"
// root
const char* const kName = "name";                     // string
const char* const kPort = "port";                     // int
const char* const kOnlyFrom = "only_from";            // seq
const char* const kIpv6 = "ipv6";                     // bool
const char* const kExecute = "execute";               // seq
const char* const kHost = "host";                     // seq
const char* const kAsync = "async";                   // bool
const char* const kSectionFlush = "section_flush";    // bool
const char* const kGlobalEncrypt = "encrypted";       // bool
const char* const kGlobalPassword = "passphrase";     // string
const char* const kGlobalWmiTimeout = "wmi_timeout";  // int

const char* const kRealTime = "realtime";    // map
const char* const kRtTimeout = "timeout";    // int
const char* const kRtEncrypt = "encrypted";  // bool
const char* const kRtRun = "run";            // seq

const char* const kSectionsEnabled = "sections";            // seq
const char* const kSectionsDisabled = "disabled_sections";  // seq

const char* const kLogging = "logging";    // map
const char* const kLogPublic = "public";   // bool
const char* const kLogDebug = "debug";     // string no, yes, all
const char* const kLogWinDbg = "windbg";   // bool
const char* const kLogEvent = "eventlog";  // bool
const char* const kLogFile = "file";       // string

// group plugins
const char* const kPluginsFolders = "folders";            // seq
const char* const kPluginsDefaultFolderMark = "default";  // seq
const char* const kPluginsExecution = "execution";        // seq
const char* const kPluginMaxWait = "max_wait";            // int
const char* const kPluginAsyncStart = "async_start";      // bool

const char* const kPluginUserFolder = "@user";   // to be replaced
const char* const kPluginCoreFolder = "@core";   // to be replaced
const char* const kProgramDataFolder = "@data";  // to be replaced

// plugins.execution
const char* const kPluginPattern = "pattern";     // string
const char* const kPluginTimeout = "timeout";     // int
const char* const kPluginAsync = "async";         // bool
const char* const kPluginRetry = "retry_count";   // int
const char* const kPluginCacheAge = "cache_age";  // int
const char* const kPluginExe = "exe";             // string
const char* const kPluginRun = "run";             // bool

// group "winperf"
// root
const char* const kWinPerfCounters = "counters";      // seq
const char* const kWinPerfExe = "exe";                // string
const char* const kWinPerfPrefixName = "prefix";      // string
const char* const kWinPerfPrefixDefault = "winperf";  // string
const char* const kWinPerfTimeout = "timeout";        // int

// group "logwatch"
// root
const char* const kLogWatchEventSendall = "sendall";     // bool
const char* const kLogWatchEventVistaApi = "vista_api";  // bool
const char* const kLogWatchEventLogFile = "logfile";     // string
const char* const kLogWatchEvent_Name = "name";          // string
const char* const kLogWatchEvent_Level = "level";        // string
const char* const kLogWatchEvent_Context = "context";    // bool

const char* const kLogWatchEvent_ParamWords[] = {
    "off",   // 0
    "all",   // 1
    "warn",  // 2
    "crit",  // 3
};

// winperf.counters[].
const char* const kWinPerfId = "id";      // string
const char* const kWinPerfName = "name";  // string

// group "logfiles"
const char* const kLogFilesView = "view";  // seq

// logfiles.view[]. subgroup is array from:
const char* const kLogFilesObserve = "observe";          // string
const char* const kLogFilesName = "name";                // string
const char* const kLogFilesDescription = "description";  // string
const char* const kLogFilesRotated = "rotated";          // bool
const char* const kLogFilesContext = "context";          // bool
const char* const kLogFilesFromStart = "from_start";     // bool
const char* const kLogFilesPatterns = "patterns";        // map

// criteria logfiles.view.[index].patterns.
const char* const kLogFilesOk = "ok";          // string
const char* const kLogFilesCrit = "crit";      // string
const char* const kLogFilesWarn = "warn";      // string
const char* const kLogFilesIgnore = "ignore";  // string

const char* const kLogFilesConfig = "config";    // string
const char* const kLogFilesGlob = "glob";        // string
const char* const kLogFilesPattern = "pattern";  // string

// group "ps"
const char* const kPsUseWmi = "use_wmi";      // bool
const char* const kPsFullPath = "full_path";  // bool

// group "fileinfo"
const char* const kFileInfoPath = "path";  // sequence

// group "mrpe"
const char* const kMrpeConfig = "config";  // sequence

}  // namespace vars
}  // namespace cma::cfg
