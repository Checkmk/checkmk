// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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

bool PatchOldFilesWithDatHash();  // the part of engine

// optionally move protocol file from old location to new one
// return true if location are different
bool UpdateProtocolFile(std::wstring_view new_location,
                        std::wstring_view old_location);

// Intermediate API
// accepts only "checkmk\\agent" ending path as program data
// return count of files copied
enum class CopyFolderMode { keep_old, remove_old };
int CopyAllFolders(const std::filesystem::path &LegacyRoot,
                   const std::filesystem::path &ProgramData,
                   CopyFolderMode mode);

int CopyRootFolder(const std::filesystem::path &LegacyRoot,
                   const std::filesystem::path &ProgramData);

// INI --------------------------------------------
// Intermediate API used in indirectly in production
bool ConvertIniFiles(const std::filesystem::path &LegacyRoot,
                     const std::filesystem::path &ProgramData);
bool ConvertLocalIniFile(const std::filesystem::path &LegacyRoot,
                         const std::filesystem::path &ProgramData);
bool ConvertUserIniFile(const std::filesystem::path &LegacyRoot,
                        const std::filesystem::path &ProgramData,
                        bool LocalFileExists);

std::filesystem::path CreateUserYamlFromIni(
    const std::filesystem::path &ini_file,      // ini file to use
    const std::filesystem::path &program_data,  // directory to send
    const std::string &yaml_name                // name to be used in output
    ) noexcept;

std::filesystem::path CreateBakeryYamlFromIni(
    const std::filesystem::path &ini_file,      // ini file to use
    const std::filesystem::path &program_data,  // directory to send
    const std::string &yaml_name                // name to be used in output
    ) noexcept;

// after upgrade we create in root our protocol
bool CreateProtocolFile(const std::filesystem::path &dir,
                        std::string_view OptionalContent);
// LOW level
// gtest [+]
std::optional<YAML::Node> LoadIni(std::filesystem::path File);
// gtest [+]
bool StoreYaml(const std::filesystem::path &File, YAML::Node Yaml,
               const std::string &Comment) noexcept;
// gtest [+]
bool IsBakeryIni(const std::filesystem::path &Path) noexcept;
// gtest [+]
std::string MakeComments(const std::filesystem::path &SourceFilePath,
                         bool Bakery) noexcept;

[[nodiscard]] bool CreateFolderSmart(const std::filesystem::path &tgt) noexcept;
bool IsPathProgramData(const std::filesystem::path &program_data);
[[nodiscard]] bool IsFileNonCompatible(
    const std::filesystem::path &fname) noexcept;
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
int GetServiceStatusByName(const std::wstring &Name);
int GetServiceStatus(SC_HANDLE ServiceHandle);
// this is full-featured function
// may be used in production as part of top level API
bool StopWindowsService(std::wstring_view service_name);

bool IsLegacyAgentActive();
bool ActivateLegacyAgent();
bool DeactivateLegacyAgent();

// limited function, just to have for testing
bool StartWindowsService(const std::wstring &Name);

// used to wait for some long starting/stopping drivers
int WaitForStatus(std::function<int(const std::wstring &)> StatusChecker,
                  std::wstring_view ServiceName, int ExpectedStatus, int Time);

// used to copy folders from legacy agent to programdata
int CopyFolderRecursive(
    const std::filesystem::path &source, const std::filesystem::path &target,
    std::filesystem::copy_options copy_mode,
    const std::function<bool(std::filesystem::path)> &predicate) noexcept;

bool RunDetachedProcess(const std::wstring &Name);
namespace details {
bool IsIgnoredFile(const std::filesystem::path &filename);
}

std::filesystem::path ConstructProtocolFileName(
    const std::filesystem::path &dir) noexcept;

// API to fix hash in 1.5 agent
constexpr std::string_view kHashName = "hash";
constexpr std::string_view kIniHashMarker = "# agent hash: ";
constexpr std::string_view kStateHashMarker = "'installed_aghash': '";
std::filesystem::path FindOldIni();
std::filesystem::path FindOldState();
std::string GetNewHash(const std::filesystem::path &dat) noexcept;

std::string GetOldHashFromIni(const std::filesystem::path &ini) noexcept;
std::string GetOldHashFromState(const std::filesystem::path &state) noexcept;
std::string GetOldHashFromFile(const std::filesystem::path &ini,
                               std::string_view marker) noexcept;

bool PatchHashInFile(const std::filesystem::path &ini, const std::string &hash,
                     std::string_view marker) noexcept;
bool PatchIniHash(const std::filesystem::path &ini,
                  const std::string &hash) noexcept;
bool PatchStateHash(const std::filesystem::path &ini,
                    const std::string &hash) noexcept;
std::filesystem::path FindOwnDatFile();
std::filesystem::path ConstructDatFileName() noexcept;

}  // namespace cma::cfg::upgrade

namespace cma::cfg::rm_lwa {
bool IsRequestedByRegistry();
void SetAlreadyRemoved();
bool IsAlreadyRemoved();
bool IsToRemove();
void Execute();

}  // namespace cma::cfg::rm_lwa

#endif  // upgrade_h__
