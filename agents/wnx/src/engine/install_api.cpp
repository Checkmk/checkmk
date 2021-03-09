
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

namespace cma::install {
bool g_use_script_to_install{true};

bool UseScriptToInstall() { return g_use_script_to_install; }

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

    auto ret = cma::ntfs::Remove(File, ec);
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
    const std::filesystem::path& msi) {
    namespace fs = std::filesystem;
    // msiexecs' parameters below are not fixed unfortunately
    // documentation is scarce and method of installation in MK
    // is not a special standard
    std::wstring command = L"/i " + msi.wstring();

    std::filesystem::path log_file_name = cma::cfg::GetLogDir();
    std::error_code ec;
    if (!fs::exists(log_file_name, ec)) {
        XLOG::d("Log file path doesn't '{}' exist. Fallback to install.",
                log_file_name.u8string());
        log_file_name = cma::cfg::GetUserInstallDir();
    }

    log_file_name /= kMsiLogFileName;

    command += L" /qn";  // but MS doesn't care at all :)

    if (GetInstallMode() == InstallMode::reinstall) {
        // this is REQUIRED when we are REINSTALLING already installed
        // package
        command += L" REINSTALL = ALL REINSTALLMODE = amus";
    }

    command += L" /L*V ";  // quoting too!
    command += log_file_name;
    command += L"";

    return {command, log_file_name.wstring()};
}

void ExecuteUpdate::backupLog() const {
    namespace fs = std::filesystem;

    std::error_code ec;
    fs::path log_file_name{log_file_name_};

    if (!fs::exists(log_file_name, ec)) return;

    XLOG::l.i("File '{0}' exists, backing up to '{0}.bak'",
              log_file_name.u8string());

    auto log_bak_file_name = log_file_name;
    log_bak_file_name.replace_extension(".log.bak");

    auto success = MvFile(log_file_name, log_bak_file_name);

    if (!success) {
        XLOG::d("Backing up of msi log failed");
    }
}

void ExecuteUpdate::determineFilePaths() {
    namespace fs = std::filesystem;

    base_script_file_ = cfg::GetRootUtilsDir();
    base_script_file_ /= cfg::files::kExecuteUpdateFile;

    temp_script_file_ =
        fs::temp_directory_path() /
        fmt::format("cmk_update_agent_{}", ::GetCurrentProcessId()) /
        cfg::files::kExecuteUpdateFile;
}

bool ExecuteUpdate::copyScriptToTemp() const {
    namespace fs = std::filesystem;

    try {
        fs::create_directories(temp_script_file_.parent_path());
        fs::copy_file(base_script_file_, temp_script_file_,
                      fs::copy_options::overwrite_existing);
        return fs::exists(temp_script_file_);
    } catch (const fs::filesystem_error& e) {
        XLOG::l("Failure in copyScriptToTemp '{}' f1= '{}' f2= '{}'", e.what(),
                e.path1().u8string(), e.path2().u8string());
    }

    return false;
}

void ExecuteUpdate::prepare(const std::filesystem::path& exe,
                            const std::filesystem::path& msi,
                            bool validate_script_exists) {
    namespace fs = std::filesystem;

    auto [command_tail, log_file_name] = MakeCommandLine(msi);
    log_file_name_ = log_file_name;

    std::error_code ec;

    // no validate -> new
    // validate and script is present -> new
    // validate and script is absent -> old
    auto required_script_absent =
        validate_script_exists && !fs::exists(base_script_file_, ec);

    if (UseScriptToInstall() && !required_script_absent) {
        fs::path script_log(cfg::GetLogDir());
        script_log /= "execute_script.log";

        command_ = fmt::format(
            LR"("{}" "{}" "{}" "{}")",
            temp_script_file_.wstring(),  // path/to/execute_update.cmd
            exe.wstring(),                // path/to/msiexec.exe
            command_tail,           // "/i check_mk_agent.msi /qn /L*V log"
            script_log.wstring());  // script.log
    } else {
        command_ = exe.wstring() + L" " + command_tail;
    }

    XLOG::l.i("File '{}' exists\n\tCommand is '{}'", msi.u8string(),
              wtools::ConvertToUTF8(command_));
}

// check that update exists and exec it
// returns true when update found and ready to exec
std::pair<std::wstring, bool> CheckForUpdateFile(
    std::wstring_view msi_name, std::wstring_view msi_dir,
    UpdateProcess start_update_process, std::wstring_view backup_dir) {
    namespace fs = std::filesystem;

    // find path to msiexec, in Windows it is in System32 folder
    const auto exe = cma::cfg::GetMsiExecPath();
    if (exe.empty()) {
        return {{}, false};
    }

    // check file existence
    fs::path msi_base{msi_dir};
    msi_base /= msi_name;
    std::error_code ec;
    if (!fs::exists(msi_base, ec)) {
        return {{}, false};
    }

    if (!NeedInstall(msi_base, backup_dir)) {
        return {{}, false};
    }

    // Move file to temporary folder
    auto msi_to_install = MakeTempFileNameInTempPath(msi_name);
    if (msi_to_install.empty()) {
        return {{}, false};
    }

    // remove target file
    if (RmFile(msi_to_install)) {
        // actual move
        if (!MvFile(msi_base, msi_to_install)) {
            return {{}, false};
        }
        BackupFile(msi_to_install, backup_dir);

    } else {
        // THIS BRANCH TESTED MANUALLY
        XLOG::l.i("Fallback to use random name");
        auto temp_name = GenerateTempFileNameInTempPath(msi_name);
        if (temp_name.empty()) {
            return {{}, false};
        }
        if (!MvFile(msi_base, temp_name)) {
            return {{}, false};
        }

        msi_to_install = temp_name;
        BackupFile(msi_to_install, backup_dir);
        XLOG::l.i("Installing '{}'", msi_to_install.u8string());
    }

    try {
        ExecuteUpdate eu;
        eu.prepare(exe, msi_to_install, true);
        eu.backupLog();

        if (start_update_process == UpdateProcess::skip) {
            XLOG::l.i("Actual Updating is disabled");
            return {eu.getCommand(), true};
        }

        if (!eu.copyScriptToTemp()) {
            XLOG::l("Can't copy script to temp");
            return {{}, false};
        }

        auto command = eu.getCommand();
        return {command, tools::RunStdCommand(command, false, TRUE) != 0};
    } catch (const std::exception& e) {
        XLOG::l("Unexpected exception '{}' during attempt to exec update ",
                e.what());
    }
    { return {{}, false}; }
}

};  // namespace cma::install
