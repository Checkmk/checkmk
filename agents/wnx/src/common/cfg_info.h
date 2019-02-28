// Configuration Parameters for whole Agent
// Engine independent parameters
// No C++ file
#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <shlobj.h>  // known path

#include <chrono>
#include <filesystem>
#include <string>

#include "yaml-cpp/yaml.h"

#include "common/cfg_yaml.h"
namespace XLOG {

// windows specific Event Log
enum class EventLevel : int {
    kLogCritical = 1,
    kLogError = 2,
    kLogWarning = 3,
    kLogInformation = 4,
    kLogSuccess = 99
};

// recommended but not obligatory to use
// useful when filtering data in the event log
enum EventClass {
    kBadException = 4,  // exception is strange
    kBadLogic = 12,     // logic is not a good one
    kDefault = 20       // this is default value
};
// end of windows specific

}  // namespace XLOG

namespace cma::cfg {
enum LogLevel { kLogBase = 0, kLogDebug = 1, kLogAll = 2 };

constexpr int kDefaultLogLevel = kLogBase;

// #TODO CONFIRM VALUE:
constexpr int kDefaultWmiTimeout = 3;  // seconds, this is Windows FAIL

constexpr int kDefaultRealtimeTimeout = 90;  // seconds

// #TODO CONFIRM VALUE:
constexpr int kMinimumCacheAge = 120;

// #TODO CONFIRM VALUE:
constexpr uint16_t kMainPort = 6556;

// #TODO CONFIRM VALUE:
constexpr int kDefaultPluginTimeout = 11;  // seconds

// #TODO CONFIRM VALUE:
constexpr int kDefaultWinPerfTimeout = 11;  // seconds

// #TODO CONFIRM VALUE:
constexpr int kDefaultAgentMaxWait = 15;  // max time agent waits for a sections

// #TODO CONFIRM VALUE:
constexpr int kDefaultAgentMinWait = 1;  // max time agent waits for a sections

const char* const kDefaultLogFileName = "check_mk.log";
constexpr wchar_t kAppDataCompanyName[] = L"CheckMK";
constexpr char kDefaultEventLogName[] =
    "CheckMK";  // name for windows event log
const wchar_t* const kAppDataAppName = L"Agent";
const wchar_t* const kDefaultConfigCacheFileName = L"check_mk.cached.yml";

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
const std::wstring FindExeFileOnPath(const std::wstring File);
const std::wstring FindConfigFile(std::filesystem::path Dir,
                                  const std::wstring File);

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
    using namespace std::filesystem;
    path r = Root;
    r = r / kSolutionTestFilesFolderName / kSolutionUnitTestsFolderName;
    return r.lexically_normal();
}

inline std::filesystem::path MakePathToConfigTestFiles(std::wstring Root) {
    using namespace std::filesystem;
    path r = Root;
    r = r / kSolutionTestFilesFolderName / kSolutionConfigTestFilesFolderName;
    return r.lexically_normal();
}

// Directories
namespace dirs {
// Program Files/check_mk_service/
constexpr const wchar_t* kAgentPlugins = L"plugins";      // plugins from CMK
constexpr const wchar_t* kAgentBin = L"bin";              // legacy for OHM
constexpr const wchar_t* kAgentProviders = L"providers";  // only agent's exe
constexpr const wchar_t* kAgentUtils = L"utils";          // anything to use
constexpr const wchar_t* kAgentMrpe = L"mrpe";            // mrpe

// ProgramData/CheckMK/Agent
constexpr const wchar_t* kCache = L"cache";          // owned by agent
constexpr const wchar_t* kUserPlugins = L"plugins";  // owned by user
constexpr const wchar_t* kLocal = L"local";          // owned by user
constexpr const wchar_t* kBakery = L"bakery";        // owned by site
constexpr const wchar_t* kState = L"state";          // owned by plugins
constexpr const wchar_t* kPluginConfig = L"config";  // owned by plugins

constexpr const wchar_t* kSpool = L"spool";  // owned by user/sys plugins
constexpr const wchar_t* kTemp = L"temp";    // owned by user plugins

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

};  // namespace envs

enum EventLevels { kOff = -1, kAll = 0, kWarn, kCrit };
constexpr auto kInitialPos = std::numeric_limits<uint64_t>::max();
inline const std::chrono::seconds G_DefaultDelayOnFail(3600);

};  // namespace cma::cfg
