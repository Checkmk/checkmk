
// provides api to automatic install MSI files by service

#pragma once
#ifndef install_api_h__
#define install_api_h__

#include <filesystem>
#include <string>

namespace cma {

namespace install {
enum UpdateType { kMsiExec, kMsiExecQuiet };
constexpr const wchar_t* const kDefaultMsiFileName = L"check_mk_agent.msi";

// TEST(InstallAuto, TopLevel)
// StartUpdateProcess == false when we only testing functionality
// BackupPath may be empty, normally points out on the install folder
// DirWithMsi is update dir in ProgramData
bool CheckForUpdateFile(const std::wstring& Name,
                        const std::wstring& DirWithMsi, UpdateType Update,
                        bool StartUpdateProcess,
                        const std::wstring& BackupPath = L"");

std::filesystem::path MakeTempFileNameInTempPath(const std::wstring& Name);

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

// noexcept check whther incoming file is newer
bool NeedInstall(const std::filesystem::path& IncomingFile,
                 const std::filesystem::path& BackupDir) noexcept;
// ****************************************

}  // namespace install

};  // namespace cma

#endif  // install_api_h__
