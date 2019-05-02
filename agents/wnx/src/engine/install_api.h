
// provides api to automatic install MSI files by service

#pragma once
#ifndef install_api_h__
#define install_api_h__

#include <filesystem>
#include <string>
#include <string_view>

namespace cma {

namespace install {
enum class UpdateType { exec_normal, exec_quiet };
enum class UpdateProcess { execute, skip };
constexpr const std::wstring_view kDefaultMsiFileName = L"check_mk_agent.msi";

// TEST(InstallAuto, TopLevel)
// set StartUpdateProcess to 'skip' to test functionality
// BackupPath may be empty, normally points out on the install folder
// DirWithMsi is update dir in ProgramData
bool CheckForUpdateFile(std::wstring_view Name, std::wstring_view DirWithMsi,
                        UpdateType Update, UpdateProcess StartUpdateProcess,
                        std::wstring_view BackupPath = L"");

std::filesystem::path MakeTempFileNameInTempPath(std::wstring_view Name);

// internal API with diag published to simplify testing or for later use
// ****************************************
// TEST(InstallAuto, LowLevel)
// Diagnostic is cma::install!

// noexcept remove file
bool RmFile(const std::filesystem::path& File) noexcept;

// noexcept move file
bool MvFile(const std::filesystem::path& Old,
            const std::filesystem::path& New) noexcept;

// noexcept backup file(if possible)
void BackupFile(const std::filesystem::path& File,
                const std::filesystem::path& Dir) noexcept;

// noexcept check whether incoming file is newer
bool NeedInstall(const std::filesystem::path& IncomingFile,
                 const std::filesystem::path& BackupDir) noexcept;
// ****************************************

}  // namespace install

};  // namespace cma

#endif  // install_api_h__
