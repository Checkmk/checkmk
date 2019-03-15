#ifndef upgrade_h__
#define upgrade_h__

#pragma once

#include <functional>
#include <string>
#include <string_view>

#include "common/wtools.h"

#include "logger.h"

#include "cfg.h"

namespace cma::cfg::upgrade {
constexpr std::string_view kBakeryMarker =
    "# Created by Check_MK Agent Bakery.";

// Main API
// ********************************
// The only API used in Production
bool UpgradeLegacy(bool ForceUpgrade = false);

// Intermediate API used in testing
int CopyAllFolders(const std::filesystem::path& LegacyRoot,
                   const std::filesystem::path& ProgramData);
int CopyRootFolder(const std::filesystem::path& LegacyRoot,
                   const std::filesystem::path& ProgramData);

// INI --------------------------------------------
// Intermediate API used in testing and indirectly in production
bool ConvertIniFiles(const std::filesystem::path& LegacyRoot,
                     const std::filesystem::path& ProgramData);
bool ConvertLocalIniFile(const std::filesystem::path& LegacyRoot,
                         const std::filesystem::path& ProgramData);
bool ConvertUserIniFile(const std::filesystem::path& LegacyRoot,
                        const std::filesystem::path& ProgramData,
                        bool LocalFileExists);

// This function will use correct extension and correct sub path
std::filesystem::path CreateYamlFromIniSmart(
    const std::filesystem::path IniFile,     // ini file to use
    const std::filesystem::path Pd,          // directory to send
    const std::string YamlName,              // name to be used in output
    bool ForceBakeryFile = false) noexcept;  // in some create bakery!

// after upgrade we create in root our protocol
bool CreateProtocolFile(std::filesystem::path ProtocolFile,
                        const std::string_view OptionalContent);
// LOW level
// gtest [+]
std::optional<YAML::Node> LoadIni(std::filesystem::path File);
// gtest [+]
bool StoreYaml(const std::filesystem::path File, const YAML::Node Yaml,
               const std::string Comment) noexcept;
// gtest [+]
bool IsBakeryIni(const std::filesystem::path Path) noexcept;
// gtest [+]
std::string MakeComments(const std::filesystem::path SourceFilePath,
                         bool Bakery) noexcept;
// --------------------------------------------

// Intermediate API used in testing
// gtest [+]
bool FindStopDeactivateLegacyAgent();

// Intermediate API used ONLY in testing
// we will not start LWA again
bool FindActivateStartLegacyAgent(
    bool StartOhm = false);  // StartOhm only for testing!

// Low Level API
std::wstring FindLegacyAgent();
int GetServiceStatusByName(const std::wstring& Name);
int GetServiceStatus(SC_HANDLE ServiceHandle);

bool IsLegacyAgentActive();
bool ActivateLegacyAgent();
bool DeactivateLegacyAgent();

// this is full-featured function
// may be used in production as part of top level API
bool StopWindowsService(const std::wstring& Name);

// limited function, just to have for testing
bool StartWindowsService(const std::wstring& Name);

// used to wait for some long starting/stopping drivers
int WaitForStatus(std::function<int(const std::wstring&)> StatusChecker,
                  const std::wstring& ServiceName, int ExpectedStatus,
                  int Time);

// used to copy folders from legacy agent to programdata
int CopyFolderRecursive(
    const std::filesystem::path& Source, const std::filesystem::path& Target,
    const std::function<bool(std::filesystem::path)>& Predicate) noexcept;

bool RunDetachedProcess(const std::wstring& Name);

}  // namespace cma::cfg::upgrade

#endif  // upgrade_h__
