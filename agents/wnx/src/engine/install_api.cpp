
// install MSI automatic

#include "stdafx.h"

#include <filesystem>
#include <string>

#include "common/wtools.h"   // converts
#include "tools/_process.h"  // start process

#include "cfg.h"
#include "logger.h"

#include "install_api.h"

namespace cma {

namespace install {

std::filesystem::path MakeTempFileNameInTempPath(const std::wstring& Name) {
    namespace fs = std::filesystem;
    // Find Temporary Folder
    fs::path temp_folder = cma::tools::win::GetTempFolder();
    std::error_code ec;
    if (!fs::exists(temp_folder, ec)) {
        XLOG::l("Updating is NOT possible, temporary folder not found [{}]",
                ec.value());
        return {};
    }

    return temp_folder / Name;
}

// remove file with diagnostic
// for internal use by cma::install
bool RmFile(const std::filesystem::path& File) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(File, ec)) return true;

    auto ret = fs::remove(File, ec);
    if (!ret) {
        XLOG::l("Updating is NOT possible, can't delete file '{}', error [{}]",
                File.u8string(), ec.value());
        return false;
    }
    XLOG::l.i("File '{}'was removed", File.u8string());
    return true;
}

// MOVE(rename) file with diagnostic
// for internal use by cma::install
bool MvFile(const std::filesystem::path& Old,
            const std::filesystem::path& New) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::rename(Old, New, ec);
    if (ec.value()) {
        XLOG::l(
            "Updating is NOT possible, can't move file '{}' to '{}', error [{}]",
            Old.u8string(), New.u8string(), ec.value());
        return false;
    }

    XLOG::l.i("File '{}' was moved successfully to '{}'", Old.u8string(),
              New.u8string());
    return true;
}

// store file in the folder
// used to save last installed MSI
// no return because we will install new MSI always
void BackupFile(const std::filesystem::path& File,
                const std::filesystem::path& Dir) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;

    if (Dir.empty() || !fs::exists(Dir, ec) || !fs::is_directory(Dir, ec)) {
        XLOG::l("Backup Path '{}' can't be used", Dir.u8string());
        return;
    }

    if (File.empty() || !fs::exists(File, ec) ||
        !fs::is_regular_file(File, ec)) {
        XLOG::l("Backup of the '{}' impossible", File.u8string());
        return;
    }

    auto fname = File.filename();
    fs::copy_file(File, Dir / fname, fs::copy_options::overwrite_existing, ec);
    if (ec.value() != 0) {
        XLOG::l("Backup of the '{}' in '{}' failed with error [{}]",
                File.u8string(), Dir.u8string(), ec.value());
    }

    XLOG::l.i("Backup of the '{}' in '{}' succeeded", File.u8string(),
              Dir.u8string());
}

// logic was copy pasted from the cma::cfg::cap::NeedReinstall
// return true when BackupDir is absent, BackupDir/IncomingFile.filename absent
// or when IncomingFile is newer than BackupDir/IncomingFile.filename
// Diagnostic for the "install" case
bool NeedInstall(const std::filesystem::path& IncomingFile,
                 const std::filesystem::path& BackupDir) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;

    if (!fs::exists(IncomingFile, ec)) {
        XLOG::d.w(
            "Source File '{}' is absent, installation not required and this is strange",
            IncomingFile.u8string());
        return false;
    }

    if (!fs::exists(BackupDir, ec)) {
        XLOG::l.crit(
            "Target folder '{}' absent, Agent Installation is broken. We try to continue.",
            BackupDir.u8string());
        return true;
    }

    // now both file are present
    auto fname = IncomingFile.filename();
    auto saved_file = BackupDir / fname;
    if (!fs::exists(saved_file, ec)) {
        XLOG::l.i("First Update", BackupDir.u8string());
        return true;
    }

    auto target_time = fs::last_write_time(saved_file, ec);
    auto src_time = fs::last_write_time(IncomingFile, ec);
    return src_time > target_time;
}

// check that update exists and exec it
// returns true when update found and ready to exec
bool CheckForUpdateFile(const std::wstring& Name,
                        const std::wstring& DirWithMsi, UpdateType Update,
                        bool StartUpdateProcess,
                        const std::wstring& BackupPath) {
    namespace fs = std::filesystem;

    // find path to msiexec, in Windows it is in System32 folder
    const auto exe = cma::cfg::GetMsiExecPath();
    if (exe.empty()) return false;

    // check file existence
    fs::path msi_base = DirWithMsi;
    msi_base /= Name;
    std::error_code ec;
    if (!fs::exists(msi_base, ec)) return false;  // this is ok

    switch (Update) {
        case kMsiExec:
        case kMsiExecQuiet:
            break;
        default:
            XLOG::l("Invalid Option {}", Update);
            return false;
    }

    if (!NeedInstall(msi_base, BackupPath)) return false;

    // Move file to temporary folder
    auto msi_to_install = MakeTempFileNameInTempPath(Name);
    if (msi_to_install.empty()) return false;

    // remove target file
    if (!RmFile(msi_to_install)) return false;

    // actual move
    if (!MvFile(msi_base, msi_to_install)) return false;

    BackupFile(msi_to_install, BackupPath);

    // Prepare Command
    std::wstring command = exe + L" ";
    command = command + L" /i " + msi_to_install.wstring() +
              L" REINSTALL=ALL REINSTALLMODE=amus ";

    if (Update == kMsiExecQuiet)  // this is only normal method
        command += L" /quiet";    // but MS doesn't care at all :)

    XLOG::l.i("File '{}' exists\n Command is '{}'", msi_to_install.u8string(),
              wtools::ConvertToUTF8(command.c_str()));

    if (!StartUpdateProcess) {
        XLOG::l.i("Actual Updating is disabled");
        return true;
    }

    return cma::tools::RunStdCommand(command, false, TRUE);
}

}  // namespace install
};  // namespace cma
