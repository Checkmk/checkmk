
// install MSI automatic

#include "stdafx.h"

#include "install_api.h"

#include <filesystem>
#include <string>

#include "cfg.h"
#include "cma_core.h"
#include "common/wtools.h"  // converts
#include "logger.h"
#include "tools/_process.h"  // start process

namespace cma {

namespace install {

InstallMode G_InstallMode = InstallMode::normal;
InstallMode GetInstallMode() { return G_InstallMode; }

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

// makes in temp own folder with name check_mk_agent_<pid>_<number>
// returns path to this folder with msi_name
// on fail returns empty
std::filesystem::path GenerateTempFileNameInTempPath(
    std::wstring_view msi_name) {
    namespace fs = std::filesystem;
    // Find Temporary Folder
    fs::path temp_folder = cma::tools::win::GetTempFolder();
    std::error_code ec;
    if (!fs::exists(temp_folder, ec)) {
        XLOG::l("Updating is NOT possible, temporary folder not found [{}]",
                ec.value());
        return {};
    }

    auto pid = ::GetCurrentProcessId();
    static int counter = 0;
    counter++;

    fs::path ret_path;
    int attempt = 0;
    while (1) {
        auto folder_name = fmt::format("check_mk_agent_{}_{}", pid, counter);
        ret_path = temp_folder / folder_name;
        if (!fs::exists(ret_path, ec) && fs::create_directory(ret_path, ec))
            break;

        XLOG::l("Proposed folder exists '{}'", ret_path.u8string());
        attempt++;
        if (attempt >= 5) {
            XLOG::l("Can't find free name for folder");

            return {};
        }
    }

    return ret_path / msi_name;
}

static void LogPermissions(const std::string& file) {
    try {
        wtools::ACLInfo acl(file.c_str());
        auto ret = acl.query();
        if (ret == S_OK)
            XLOG::l("Permissions:\n{}", acl.output());
        else
            XLOG::l("Permission access failed with error {:#X}", ret);
    } catch (const std::exception& e) {
        XLOG::l("Exception hit in bad place {}", e.what());
    }
}

static bool RmFileWithRename(const std::filesystem::path& File,
                             std::error_code ec) {
    namespace fs = std::filesystem;
    XLOG::l(
        "Updating is NOT possible, can't delete file '{}', error [{}]. Trying rename.",
        File.u8string(), ec.value());

    LogPermissions(File.u8string());
    LogPermissions(File.parent_path().u8string());

    auto file = File;
    fs::rename(File, file.replace_extension(".old"), ec);
    std::error_code ecx;
    if (!fs::exists(File, ecx)) {
        XLOG::l.i("Renamed '{}' to '{}'", File.u8string(), file.u8string());
        return true;  // success
    }

    XLOG::l(
        "Updating is STILL NOT possible, can't RENAME file '{}' to '{}', error [{}]",
        File.u8string(), file.u8string(), ec.value());
    return false;
}

// remove file with diagnostic
// for internal use by cma::install
bool RmFile(const std::filesystem::path& File) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(File, ec)) {
        XLOG::l.t("File '{}' is absent, no need to delete", File.u8string());
        return true;
    }

    auto ret = fs::remove(File, ec);
    if (ret || ec.value() == 0) {  // either deleted or disappeared
        XLOG::l.i("File '{}'was removed", File.u8string());
        return true;
    }

    return RmFileWithRename(File, ec);
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

std::pair<std::wstring, std::wstring> MakeCommandLine(
    const std::filesystem::path& msi, UpdateType update_type) {
    // msiexecs' parameters below are not fixed unfortunately
    // documentation is scarce and method of installation in MK
    // is not a special standard
    std::wstring command = L" /i " + msi.wstring();

    std::filesystem::path log_file_name = cma::cfg::GetLogDir();
    log_file_name /= kMsiLogFileName;

    if (update_type == UpdateType::exec_quiet)  // this is only normal method
    {
        command += L" /qn";  // but MS doesn't care at all :)

        if (GetInstallMode() == InstallMode::reinstall) {
            // this is REQUIRED when we are REINSTALLING already installed
            // package
            command += L" REINSTALL = ALL REINSTALLMODE = amus";
        }

        command += L" /L*V ";
        command += log_file_name;
    }

    return {command, log_file_name.wstring()};
}

static void BackupLogFile(std::filesystem::path log_file_name) {
    namespace fs = std::filesystem;

    std::error_code ec;

    if (!fs::exists(log_file_name, ec)) return;

    XLOG::l.i("File '{0}' exists, backing up to '{0}.bak'",
              log_file_name.u8string());

    auto log_bak_file_name = log_file_name;
    log_bak_file_name.replace_extension(".log.bak");
    auto success = MvFile(log_file_name, log_bak_file_name);

    if (!success) XLOG::d("Backing up of msi log failed");
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
    if (RmFile(msi_to_install)) {
        // actual move
        if (!MvFile(msi_base, msi_to_install)) return false;
        BackupFile(msi_to_install, BackupPath);

    } else {
        // THIS BRANCH TESTED MANUALLY
        XLOG::l.i("Fallback to use random name");
        auto temp_name = GenerateTempFileNameInTempPath(Name);
        if (temp_name.empty()) return false;
        if (!MvFile(msi_base, temp_name)) return false;

        msi_to_install = temp_name;
        BackupFile(msi_to_install, BackupPath);
        XLOG::l.i("Installing '{}'", msi_to_install.u8string());
    }

    // Prepare Command

    auto [command_tail, log_file_name] =
        MakeCommandLine(msi_to_install, Update);

    std::wstring command = exe;
    command += L" ";
    command += command_tail;

    BackupLogFile(log_file_name);

    XLOG::l.i("File '{}' exists\n\tCommand is '{}'", msi_to_install.u8string(),
              wtools::ConvertToUTF8(command));

    if (StartUpdateProcess == UpdateProcess::skip) {
        XLOG::l.i("Actual Updating is disabled");
        return true;
    }

    return cma::tools::RunStdCommand(command, false, TRUE) != 0;
}

}  // namespace install
};  // namespace cma
