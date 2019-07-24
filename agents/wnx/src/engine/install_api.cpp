
// install MSI automatic

#include "stdafx.h"

#include "install_api.h"

#include <filesystem>
#include <string>

#include "cfg.h"
#include "common/wtools.h"  // converts
#include "logger.h"
#include "tools/_process.h"  // start process

namespace cma {

namespace install {

std::filesystem::path MakeTempFileNameInTempPath(std::wstring_view Name) {
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

    if (File.empty() || !cma::tools::IsValidRegularFile(File)) {
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
bool CheckForUpdateFile(std::wstring_view Name, std::wstring_view DirWithMsi,
                        UpdateType Update, UpdateProcess StartUpdateProcess,
                        std::wstring_view BackupPath) {
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
        case UpdateType::exec_normal:
        case UpdateType::exec_quiet:
            break;
        default:  // safety, MSVC give us no warning
            XLOG::l("Invalid Option '{}'", static_cast<int>(Update));
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

    std::wstring command = exe;

    // msiexecs' parameters below are not fixed unfortunately
    // documentation is scarce and method of installation in MK
    // is not a special standard
    command += L" /i " + msi_to_install.wstring();

    std::wstring log_file_name = cma::cfg::GetLogDir();
    log_file_name += L"\\agent_msi.log";
    if (fs::exists(log_file_name, ec)) {
        XLOG::l.i("File '{0}' exists, backing up to '{0}.bak'",
                  wtools::ConvertToUTF8(log_file_name));

        auto success = MvFile(log_file_name, log_file_name + L".bak");

        if (!success) XLOG::d("Backing up failed");
    }

    if (Update == UpdateType::exec_quiet)  // this is only normal method
    {
        command += L" /qn";  // but MS doesn't care at all :)
        command += L" /L*V ";
        command += log_file_name;
    }

    XLOG::l.i("File '{}' exists\n Command is '{}'", msi_to_install.u8string(),
              wtools::ConvertToUTF8(command.c_str()));

    if (StartUpdateProcess == UpdateProcess::skip) {
        XLOG::l.i("Actual Updating is disabled");
        return true;
    }

    return cma::tools::RunStdCommand(command, false, TRUE);
}

}  // namespace install
};  // namespace cma
