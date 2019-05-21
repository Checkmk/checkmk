#ifndef upgrade_h__
#define upgrade_h__

#pragma once

#include <functional>
#include <string>
#include <string_view>

#include "cfg.h"
#include "common/wtools.h"
#include "logger.h"

namespace cma::cfg::upgrade {
constexpr std::string_view kBakeryMarker =
    "# Created by Check_MK Agent Bakery.";

// Main API
// ********************************
// The only API used in Production
enum class Force { no, yes };
bool UpgradeLegacy(Force force_upgrade = Force::no);

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

enum class BakeryFile { normal, force };
// This function will use correct extension and correct sub path
std::filesystem::path CreateYamlFromIniSmart(
    const std::filesystem::path& ini_file,      // ini file to use
    const std::filesystem::path& program_data,  // directory to send
    const std::string& yaml_name,               // name to be used in output
    BakeryFile bakery_file_mode) noexcept;      // how create bakery yml

// after upgrade we create in root our protocol
bool CreateProtocolFile(std::filesystem::path& ProtocolFile,
                        std::string_view OptionalContent);
// LOW level
// gtest [+]
std::optional<YAML::Node> LoadIni(std::filesystem::path File);
// gtest [+]
bool StoreYaml(const std::filesystem::path& File, YAML::Node Yaml,
               const std::string& Comment) noexcept;
// gtest [+]
bool IsBakeryIni(const std::filesystem::path& Path) noexcept;
// gtest [+]
std::string MakeComments(const std::filesystem::path& SourceFilePath,
                         bool Bakery) noexcept;
// --------------------------------------------

// Intermediate API used in testing
// gtest [+]
bool FindStopDeactivateLegacyAgent();

// Intermediate API used ONLY in testing
// we will not start LWA again
enum class AddAction { nothing, start_ohm };
bool FindActivateStartLegacyAgent(AddAction action = AddAction::nothing);

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
namespace details {
bool IsIgnoredFile(const std::filesystem::path& filename);
}

}  // namespace cma::cfg::upgrade

#endif  // upgrade_h__
