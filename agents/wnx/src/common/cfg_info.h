// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// Configuration Parameters for whole Agent
// Engine independent parameters
// No C++ file
#pragma once
#define NOMINMAX     // must before every windows include
#include <shlobj.h>  // known path

#include <chrono>
#include <filesystem>
#include <string>
#include <string_view>

#include "common/cfg_yaml.h"
#include "common/yaml.h"

namespace cma {
// set only when executable works as a service
bool IsService();
bool IsTest();
}  // namespace cma

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

/// \brief  If true, than modules will be moved to %temp% for later usage
constexpr bool g_quick_module_reinstall_allowed{true};

constexpr int kBackupLogMaxCount = 5;
constexpr size_t kBackupLogMaxSize = 8 * 1024 * 1024;

constexpr uint32_t kMaxOhmErrorsBeforeRestart = 3;

constexpr int kDefaultLogLevel = kLogBase;

// Windows Wmi API timeout, decision from LWA
constexpr int kDefaultWmiTimeout = 5;  // seconds, this is Windows FAIL

// data will be send to peer during this interval
constexpr int kDefaultRealtimeTimeout = 90;  // In seconds.

constexpr int kDefaultRealtimePort = 6559;

// #TODO CONFIRM VALUE:
constexpr int kMinimumCacheAge = 120;

// Default Port for connection to client
constexpr uint16_t kMainPort = 6556;

// Default timeout for any plugin
constexpr int kDefaultPluginTimeout = 60;  // seconds

constexpr int kDefaultWinPerfTimeout = 10;  // seconds
constexpr bool kDefaultWinPerfFork = true;
constexpr bool kDefaultWinPerfTrace = false;

// #TODO Probably deprecated
constexpr int kDefaultAgentMaxWait = 15;  // max time agent waits for a sections

// This value is set when timeout was defined badly by ini/yml/user
constexpr int kDefaultAgentMinWait = 10;  // min safe timeout

constexpr const char *const kDefaultLogFileName = "check_mk.log";
constexpr const char *const kDefaultAppFileName = "check_mk_agent.exe";
constexpr char kDefaultEventLogName[] =
    "checkmk";  // name for windows event log
const wchar_t *const kAppDataAppName = L"agent";
const wchar_t *const kDefaultConfigCacheFileName = L"check_mk.cached.yml";
}  // namespace cma::cfg

// section with folder names, file names and some textual app defaults
namespace cma::cfg {
constexpr const wchar_t kAppDataCompanyName[] = L"checkmk";

// defines default behavior of the main thread
constexpr bool IsOneShotMode() { return true; }

constexpr const KNOWNFOLDERID &kPublicFolderId = FOLDERID_Public;
constexpr const KNOWNFOLDERID &kWindowsFolderId = FOLDERID_Windows;

std::string GetCurrentLogFileName();
int GetCurrentDebugLevel();
XLOG::EventLevel GetCurrentEventLevel();  // fixed at the moment on Critical
bool GetCurrentWinDbg();
bool GetCurrentEventLog();

inline const std::wstring GetDefaultPrefixName() { return L"agent: "; }

// where you can find executables
std::vector<std::wstring> &ExternalCommandPaths();

// API to find a file on exe path
std::wstring FindExeFileOnPath(const std::wstring &file_name);
std::wstring FindConfigFile(const std::filesystem::path &dir_name,
                            const std::wstring &file_name);

// API for testing and logging
std::vector<std::filesystem::path> GetExePaths();

// Directories
namespace dirs {
// Program Files/checkmk/service/
constexpr const wchar_t *kAgentPlugins = L"plugins";      // plugins from CMK
constexpr const wchar_t *kAgentProviders = L"providers";  // only agent's exe
constexpr const wchar_t *kAgentUtils = L"utils";          // anything to use
constexpr const wchar_t *kFileInstallDir = L"install";    // from here!

// ProgramData/checkmk/agent
constexpr const wchar_t *kUserBin = L"bin";  // owned by agent legacy for OHM

constexpr const wchar_t *kBackup = L"backup";             // owned by agent
constexpr const wchar_t *kUserPlugins = L"plugins";       // owned by user
constexpr const wchar_t *kLocal = L"local";               // owned by user
constexpr const wchar_t *kAgentMrpe = L"mrpe";            // owned by user
constexpr const wchar_t *kInstall = L"install";           // owned by agent
constexpr const wchar_t *kUserInstallDir = L"install";    // owned by agent
constexpr const wchar_t *kBakery = L"bakery";             // owned by site
constexpr const wchar_t *kState = L"state";               // owned by plugins
constexpr const wchar_t *kPluginConfig = L"config";       // owned by plugins
constexpr const wchar_t *kUserModules = L"modules";       // owned by agent
constexpr const wchar_t *kInstalledModules = L"modules";  // owned by agent

constexpr const wchar_t *kAuStateLocation = kPluginConfig;  // owned by plugins

constexpr const wchar_t *kSpool = L"spool";    // owned by user/sys plugins
constexpr const wchar_t *kTemp = L"tmp";       // owned by user plugins
constexpr const wchar_t *kUpdate = L"update";  // owned by agent
constexpr const wchar_t *kMrpe = L"mrpe";      // owned by user(!) for mrpe
constexpr const wchar_t *kLog = L"log";        // owned by agent

};  // namespace dirs
namespace envs {

// to inform plugins where place state file
constexpr std::string_view kMkStateDirName{"MK_STATEDIR"};
constexpr std::string_view kMkConfDirName{"MK_CONFDIR"};
constexpr std::string_view kMkLocalDirName{"MK_LOCALDIR"};
constexpr std::string_view kMkTempDirName{"MK_TEMPDIR"};
constexpr std::string_view kMkSpoolDirName{"MK_SPOOLDIR"};
constexpr std::string_view kMkPluginsDirName{"MK_PLUGINSDIR"};
constexpr std::string_view kMkLogDirName{"MK_LOGDIR"};
constexpr std::string_view kRemoteHost{"REMOTE_HOST"};
constexpr std::string_view kRemote{"REMOTE"};

constexpr std::string_view kMkInstallDirName{"MK_INSTALLDIR"};
constexpr std::string_view kMkModulesDirName{"MK_MODULESDIR"};
constexpr std::string_view kMkMsiPathName{"MK_MSI_PATH"};

};  // namespace envs

// internal and stable representation of the [logwatch] event levels
enum class EventLevels { kIgnore = -2, kOff = -1, kAll = 0, kWarn, kCrit };

// #TODO gtest
// converts from internal and stable representation
// to key word in logwatch section of the YAML config file
constexpr const char *const ConvertLogWatchLevelToString(EventLevels Lvl) {
    switch (Lvl) {
        case EventLevels::kAll:
            return vars::kLogWatchEvent_ParamWords[2];
        case EventLevels::kWarn:
            return vars::kLogWatchEvent_ParamWords[3];
        case EventLevels::kCrit:
            return vars::kLogWatchEvent_ParamWords[4];
        case EventLevels::kOff:
            return vars::kLogWatchEvent_ParamWords[1];
        case EventLevels::kIgnore:
            return vars::kLogWatchEvent_ParamWords[0];
    }

    // unreachable for GCC, Safety Guard for Microsoft
    return vars::kLogWatchEvent_ParamWords[0];
}

constexpr auto kFromBegin = std::numeric_limits<uint64_t>::max();
inline const std::chrono::seconds G_DefaultDelayOnFail(3600);

// Prefixes of mailslots' names
constexpr const char *const kServiceMailSlot = "WinAgent";      // production
constexpr const char *const kTestingMailSlot = "WinAgentTest";  // testing

};  // namespace cma::cfg
