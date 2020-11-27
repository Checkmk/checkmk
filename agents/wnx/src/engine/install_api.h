// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides api to automatic install MSI files by service

#pragma once
#ifndef install_api_h__
#define install_api_h__

#include <filesystem>
#include <string>
#include <string_view>

#include "tools/_tgt.h"

namespace cma {

namespace install {
enum class UpdateType { exec_normal, exec_quiet };
enum class UpdateProcess { execute, skip };
enum class InstallMode { normal, reinstall };
InstallMode GetInstallMode();
std::pair<std::wstring, std::wstring> MakeCommandLine(
    const std::filesystem::path& msi, UpdateType update_type);

constexpr const std::wstring_view kDefaultMsiFileName = L"check_mk_agent.msi";

constexpr const std::string_view kMsiLogFileName = "agent_msi.log";

namespace registry

{
// Names are from WIX Msi, please, check that they are in sync
const std::wstring kMsiInfoPath64 = L"SOFTWARE\\WOW6432Node\\checkmkservice";
const std::wstring kMsiInfoPath32 = L"SOFTWARE\\checkmkservice";

const std::wstring kMsiInstallFolder = L"Install_Folder";
const std::wstring kMsiInstallService = L"Install_Service";

const std::wstring kMsiRemoveLegacy = L"Remove_Legacy";
const std::wstring kMsiRemoveLegacyDefault = L"";
const std::wstring kMsiRemoveLegacyRequest = L"1";
const std::wstring kMsiRemoveLegacyAlready = L"0";

constexpr std::wstring_view kMsiPostInstallRequired = L"PostInstall_Required";
constexpr std::wstring_view kMsiPostInstallDefault = L"no";
constexpr std::wstring_view kMsiPostInstallRequest = L"yes";

inline const std::wstring GetMsiRegistryPath() {
    return tgt::Is64bit() ? registry::kMsiInfoPath64 : registry::kMsiInfoPath32;
}
};  // namespace registry

// TEST(InstallAuto, TopLevel)
// set StartUpdateProcess to 'skip' to test functionality
// BackupPath may be empty, normally points out on the install folder
// DirWithMsi is update dir in ProgramData
bool CheckForUpdateFile(std::wstring_view msi_name, std::wstring_view msi_dir,
                        UpdateType update_type,
                        UpdateProcess start_update_process,
                        std::wstring_view backup_dir = L"");

std::filesystem::path MakeTempFileNameInTempPath(std::wstring_view Name);
std::filesystem::path GenerateTempFileNameInTempPath(std::wstring_view Name);

// internal API with diag published to simplify testing or for later use
// ****************************************
// TEST(InstallAuto, LowLevel)
// Diagnostic is cma::install!

// noexcept remove file
bool RmFile(const std::filesystem::path& file_name) noexcept;

// noexcept move file
bool MvFile(const std::filesystem::path& source_file,
            const std::filesystem::path& destination_file) noexcept;

// noexcept backup file(if possible)
void BackupFile(const std::filesystem::path& file_name,
                const std::filesystem::path& backup_dir) noexcept;

// noexcept check whether incoming file is newer
bool NeedInstall(const std::filesystem::path& incoming_file,
                 const std::filesystem::path& backup_dir) noexcept;
// ****************************************

bool IsPostInstallRequired();
void ClearPostInstallFlag();

}  // namespace install
}  // namespace cma

#endif  // install_api_h__
