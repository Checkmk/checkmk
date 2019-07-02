// Configuration Parameters for whole Agent
// Engine independent parameters
// No C++ file
#pragma once
#define NOMINMAX     // must before every windows include
#include <shlobj.h>  // known path

#include <chrono>
#include <filesystem>
#include <string>

#include "common/cfg_yaml.h"
#include "yaml-cpp/yaml.h"
namespace XLOG {

// windows specific Event Log
enum class EventLevel : int {
    critical = 1,
    error = 2,
    warning = 3,
    information = 4,
    success = 99
};

// recommended but not obligatory to use
// useful when filtering data in the event log
enum EventClass {
    kBadException = 4,  // exception is strange
    kBadLogic = 12,     // logic is not a good one
    kAppDefault = 20,   // default value for any exe/test
    kSrvDefault = 30    // default value for service
};
// end of windows specific

}  // namespace XLOG

// in This section we have defaults for the configuration(YML/INI)
// values are either plain ints or plain strings
namespace cma::cfg {
enum LogLevel { kLogBase = 0, kLogDebug = 1, kLogAll = 2 };

constexpr int kBackupLogMaxCount = 5;
constexpr size_t kBackupLogMaxSize = 8 * 1024 * 1024;

constexpr int kDefaultLogLevel = kLogBase;

// #TODO CONFIRM VALUE:
constexpr int kDefaultWmiTimeout = 3;  // seconds, this is Windows FAIL

// data will be send to peer during this interval
constexpr int kDefaultRealtimeTimeout = 90;  // In seconds.

constexpr int kDefaultRealtimePort = 6559;

// #TODO CONFIRM VALUE:
constexpr int kMinimumCacheAge = 120;

// Default Port for connection to client
constexpr uint16_t kMainPort = 6556;

// Default timeout for any plugin
constexpr int kDefaultPluginTimeout = 60;  // seconds

// Windows Wmi API timeout, decision from LWA
constexpr int kDefaultWinPerfTimeout = 3;  // seconds

// #TODO Probably deprecated
constexpr int kDefaultAgentMaxWait = 15;  // max time agent waits for a sections

// This value is set when timeout was defined badly by ini/yml/user
constexpr int kDefaultAgentMinWait = 10;  // min safe timeout

constexpr const char* const kDefaultLogFileName = "check_mk.log";
constexpr const char* const kDefaultAppFileName = "check_mk_agent.exe";
constexpr char kDefaultEventLogName[] =
    "CheckMK";  // name for windows event log
const wchar_t* const kAppDataAppName = L"Agent";
const wchar_t* const kDefaultConfigCacheFileName = L"check_mk.cached.yml";
}  // namespace cma::cfg

// section with folder names, file names and some textual app defaults
namespace cma::cfg {
constexpr const wchar_t kAppDataCompanyName[] = L"CheckMK";

// defines default behavior of the main thread
constexpr bool IsOneShotMode() { return true; }

constexpr const KNOWNFOLDERID& kPublicFolderId = FOLDERID_Public;
constexpr const KNOWNFOLDERID& kWindowsFolderId = FOLDERID_Windows;

// gtest [+] everywhere
const std::string GetCurrentLogFileName();
const int GetCurrentDebugLevel();
XLOG::EventLevel GetCurrentEventLevel();  // fixed at the moment on Critical
const bool GetCurrentWinDbg();
const bool GetCurrentEventLog();

// gtest [+] everywhere
inline const std::wstring GetDefaultPrefixName() {
#if defined(LOCAL_LOG_PREFIX)
    return LOCAL_LOG_PREFIX;
#else
    return L"agent: ";
#endif
}

// where you can find executables
const std::vector<std::wstring>& ExternalCommandPaths();

// API to find a file on exe path
const std::wstring FindExeFileOnPath(const std::wstring& File);
const std::wstring FindConfigFile(const std::filesystem::path& Dir,
                                  const std::wstring& File);

// API for testing and logging
std::vector<std::filesystem::path> GetExePaths();

// below described the structure of the solution folder:
// solution root <--- Use SOLUTION_DIR define
//    \--- test_files
//            \--- unit_tests <--- MakePathToUnitTestFiles(SolutionRoot)
//            \--- config     <--- MakePathToConfigTestFiles(SolutionRoot)
inline const std::wstring kSolutionTestFilesFolderName(L"test_files");
inline const std::wstring kSolutionUnitTestsFolderName(L"unit_test");
inline const std::wstring kSolutionConfigTestFilesFolderName(L"config");

inline std::filesystem::path MakePathToUnitTestFiles(std::wstring Root) {
    namespace fs = std::filesystem;
    fs::path r = Root;
    r = r / kSolutionTestFilesFolderName / kSolutionUnitTestsFolderName;
    return r.lexically_normal();
}

inline std::filesystem::path MakePathToConfigTestFiles(std::wstring Root) {
    namespace fs = std::filesystem;
    fs::path r = Root;
    r = r / kSolutionTestFilesFolderName / kSolutionConfigTestFilesFolderName;
    return r.lexically_normal();
}

// Directories
namespace dirs {
// Program Files/check_mk_service/
constexpr const wchar_t* kAgentPlugins = L"plugins";      // plugins from CMK
constexpr const wchar_t* kAgentProviders = L"providers";  // only agent's exe
constexpr const wchar_t* kAgentUtils = L"utils";          // anything to use
constexpr const wchar_t* kFileInstallDir = L"install";    // from here!

// ProgramData/CheckMK/Agent
constexpr const wchar_t* kAgentBin = L"bin";  // owned by agent legacy for OHM

constexpr const wchar_t* kCache = L"cache";             // owned by agent
constexpr const wchar_t* kUserPlugins = L"plugins";     // owned by user
constexpr const wchar_t* kLocal = L"local";             // owned by user
constexpr const wchar_t* kAgentMrpe = L"mrpe";          // owned by user
constexpr const wchar_t* kInstall = L"install";         // owned by agent
constexpr const wchar_t* kUserInstallDir = L"install";  // owned by agent
constexpr const wchar_t* kBakery = L"bakery";           // owned by site
constexpr const wchar_t* kState = L"state";             // owned by plugins
constexpr const wchar_t* kPluginConfig = L"config";     // owned by plugins

constexpr const wchar_t* kSpool = L"spool";    // owned by user/sys plugins
constexpr const wchar_t* kTemp = L"tmp";       // owned by user plugins
constexpr const wchar_t* kUpdate = L"update";  // owned by agent
constexpr const wchar_t* kMrpe = L"mrpe";      // owned by user(!) for mrpe

};  // namespace dirs
namespace envs {

// to inform plugins where place state file
constexpr const char* const kMkStateDirName = "MK_STATEDIR";
constexpr const char* const kMkConfDirName = "MK_CONFDIR";
constexpr const char* const kMkLocalDirName = "MK_LOCALDIR";
constexpr const char* const kMkTempDirName = "MK_TEMPDIR";
constexpr const char* const kMkSpoolDirName = "MK_SPOOLDIR";
constexpr const char* const kMkPluginsDirName = "MK_PLUGINSDIR";
constexpr const char* const kMkLogDirName = "MK_LOGDIR";
constexpr const char* const kRemoteHost = "REMOTE_HOST";
constexpr const char* const kRemote = "REMOTE";

constexpr std::string_view kMkInstallDirName = "MK_INSTALLDIR";
constexpr std::string_view kMkMsiPathName = "MK_MSI_PATH";

};  // namespace envs

// internal and stable representation of the [logwatch] event levels
enum class EventLevels { kOff = -1, kAll = 0, kWarn, kCrit };

// #TODO gtest
// converts from internal and stable representation
// to key word in logwatch section of the YAML config file
constexpr const char* const ConvertLogWatchLevelToString(EventLevels Lvl) {
    switch (Lvl) {
        case EventLevels::kAll:
            return vars::kLogWatchEvent_ParamWords[1];
        case EventLevels::kWarn:
            return vars::kLogWatchEvent_ParamWords[2];
        case EventLevels::kCrit:
            return vars::kLogWatchEvent_ParamWords[3];
        case EventLevels::kOff:
            return vars::kLogWatchEvent_ParamWords[0];
    }

    // unreachable for GCC, Safety Guard for Microsoft
    return vars::kLogWatchEvent_ParamWords[0];
}

constexpr auto kInitialPos = std::numeric_limits<uint64_t>::max();
inline const std::chrono::seconds G_DefaultDelayOnFail(3600);

// Prefixes of mailslots' names
constexpr const char* const kServiceMailSlot = "WinAgent";      // production
constexpr const char* const kTestingMailSlot = "WinAgentTest";  // testing

};  // namespace cma::cfg
