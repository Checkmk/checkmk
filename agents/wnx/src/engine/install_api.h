// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides api to automatic install MSI files by service

#pragma once
#ifndef install_api_h__
#define install_api_h__

#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

#include "tools/_tgt.h"

namespace cma::install {
bool UseScriptToInstall();

std::optional<std::filesystem::path> FindProductMsi(
    std::wstring_view product_name);

enum class UpdateProcess { execute, skip };
enum class InstallMode { normal, reinstall };
InstallMode GetInstallMode();

class ExecuteUpdate {
public:
    ExecuteUpdate() { determineFilePaths(); }
    void prepare(const std::filesystem::path &exe,
                 const std::filesystem::path &msi,
                 const std::filesystem::path &recover_msi,
                 bool validate_script_exists);

    [[nodiscard]] bool copyScriptToTemp() const;
    void backupLog() const;

    [[nodiscard]] std::wstring getCommand() const noexcept { return command_; }
    [[nodiscard]] std::wstring getLogFileName() const noexcept {
        return log_file_name_;
    }

    [[nodiscard]] std::filesystem::path getTempScriptFile() const noexcept {
        return temp_script_file_;
    }

private:
    void determineFilePaths();

    std::wstring command_;
    std::wstring log_file_name_;
    std::filesystem::path base_script_file_;
    std::filesystem::path temp_script_file_;
};

constexpr std::wstring_view kDefaultMsiFileName{L"check_mk_agent.msi"};
constexpr std::string_view kMsiLogFileName{"agent_msi.log"};
constexpr std::wstring_view kAgentProductName{L"Check MK Agent 2.1"};

namespace registry {
// Names are from WIX Msi, please, check that they are in sync
const std::wstring kMsiInfoPath64 = L"SOFTWARE\\WOW6432Node\\checkmkservice";
const std::wstring kMsiInfoPath32 = L"SOFTWARE\\checkmkservice";

const std::wstring kMsiInstallFolder = L"Install_Folder";
const std::wstring kMsiInstallService = L"Install_Service";

const std::wstring kMsiRemoveLegacy = L"Remove_Legacy";
const std::wstring kMsiRemoveLegacyDefault;
const std::wstring kMsiRemoveLegacyRequest = L"1";
const std::wstring kMsiRemoveLegacyAlready = L"0";

// to control post installation phase. While set disallow any command line calls
// to service
constexpr std::wstring_view kMsiPostInstallRequired = L"PostInstall_Required";
constexpr std::wstring_view kMsiPostInstallDefault = L"no";
constexpr std::wstring_view kMsiPostInstallRequest = L"yes";

constexpr std::wstring_view kMsiMigrationRequired = L"Migration_Required";
constexpr std::wstring_view kMsiMigrationDefault;
constexpr std::wstring_view kMsiMigrationRequest = L"1";

inline std::wstring GetMsiRegistryPath() {
    return tgt::Is64bit() ? registry::kMsiInfoPath64 : registry::kMsiInfoPath32;
}
};  // namespace registry

/// Returns command and success status
/// set StartUpdateProcess to 'skip' for dry run
/// BackupPath may be empty, normally points out on the install folder
/// DirWithMsi is update dir in ProgramData
std::pair<std::wstring, bool> CheckForUpdateFile(
    std::wstring_view msi_name, std::wstring_view msi_dir,
    UpdateProcess start_update_process, std::wstring_view backup_dir);

inline std::pair<std::wstring, bool> CheckForUpdateFile(
    std::wstring_view msi_name, std::wstring_view msi_dir,
    UpdateProcess start_update_process) {
    return CheckForUpdateFile(msi_name, msi_dir, start_update_process, L"");
}

std::filesystem::path MakeTempFileNameInTempPath(std::wstring_view Name);
std::filesystem::path GenerateTempFileNameInTempPath(std::wstring_view Name);

// internal API with diag published to simplify testing or for later use
// ****************************************
// TEST(InstallAuto, LowLevel)
// Diagnostic is cma::install!

// noexcept remove file
bool RmFile(const std::filesystem::path &file_name) noexcept;

// noexcept move file
bool MvFile(const std::filesystem::path &source_file,
            const std::filesystem::path &destination_file) noexcept;

// noexcept backup file(if possible)
void BackupFile(const std::filesystem::path &file_name,
                const std::filesystem::path &backup_dir) noexcept;

// noexcept check whether incoming file is newer
bool NeedInstall(const std::filesystem::path &incoming_file,
                 const std::filesystem::path &backup_dir) noexcept;
// ****************************************

bool IsPostInstallRequired();
void ClearPostInstallFlag();

/// Returns string with error message if the installation failed.
std::optional<std::wstring> GetLastInstallFailReason();

bool IsMigrationRequired();

}  // namespace cma::install

#endif  // install_api_h__
