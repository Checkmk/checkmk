
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

std::filesystem::path MakeTempFileNameInTempPath(std::wstring_view file_name) {
    namespace fs = std::filesystem;
    // Find Temporary Folder
    fs::path temp_folder{cma::tools::win::GetTempFolder()};
    std::error_code ec;
    if (!fs::exists(temp_folder, ec)) {
        XLOG::l("Updating is NOT possible, temporary folder not found [{}]",
                ec.value());
        return {};
    }

    return temp_folder / file_name;
}

// makes in temp own folder with name check_mk_agent_<pid>_<number>
// returns path to this folder with msi_name
// on fail returns empty
std::filesystem::path GenerateTempFileNameInTempPath(
    std::wstring_view msi_name) {
    namespace fs = std::filesystem;
    // Find Temporary Folder
    fs::path temp_folder{cma::tools::win::GetTempFolder()};
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
    constexpr int max_attempts{5};
    while (true) {
        auto folder_name = fmt::format("check_mk_agent_{}_{}", pid, counter);
        ret_path = temp_folder / folder_name;
        if (!fs::exists(ret_path, ec) && fs::create_directory(ret_path, ec))
            break;

        XLOG::l("Proposed folder exists '{}'", ret_path);
        attempt++;
        if (attempt >= max_attempts) {
            XLOG::l("Can't find free name for folder");

            return {};
        }
    }

    return ret_path / msi_name;
}

static void LogPermissions(const std::string& file_name) noexcept {
    try {
        wtools::ACLInfo acl(file_name.c_str());
        auto ret = acl.query();
        if (ret == S_OK)
            XLOG::l("Permissions:\n{}", acl.output());
        else
            XLOG::l("Permission access failed with error {:#X}", ret);
    } catch (const std::exception& e) {
        XLOG::l("Exception hit in bad place {}", e.what());
    }
}

static bool RmFileWithRename(const std::filesystem::path& file_name,
                             std::error_code ec) noexcept {
    namespace fs = std::filesystem;
    XLOG::l(
        "Updating is NOT possible, can't delete file '{}', error [{}]. Trying rename.",
        file_name.u8string(), ec.value());

    LogPermissions(file_name.u8string());
    LogPermissions(file_name.parent_path().u8string());

    auto file = file_name;
    fs::rename(file_name, file.replace_extension(".old"), ec);
    std::error_code ecx;
    if (!fs::exists(file_name, ecx)) {
        XLOG::l.i("Renamed '{}' to '{}'", file_name, file);
        return true;  // success
    }

    XLOG::l(
        "Updating is STILL NOT possible, can't RENAME file '{}' to '{}', error [{}]",
        file_name, file, ec.value());
    return false;
}

// remove file with diagnostic
// for internal use by cma::install
bool RmFile(const std::filesystem::path& file_name) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(file_name, ec)) {
        XLOG::l.t("File '{}' is absent, no need to delete", file_name);
        return true;
    }

    auto ret = fs::remove(file_name, ec);
    if (ret || ec.value() == 0) {  // either deleted or disappeared
        XLOG::l.i("File '{}'was removed", file_name);
        return true;
    }

    return RmFileWithRename(file_name, ec);
}

// MOVE(rename) file with diagnostic
// for internal use by cma::install
bool MvFile(const std::filesystem::path& source_file,
            const std::filesystem::path& destination_file) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::rename(source_file, destination_file, ec);
    if (ec.value() != 0) {
        XLOG::l(
            "Updating is NOT possible, can't move file '{}' to '{}', error [{}]",
            source_file, destination_file, ec.value());
        return false;
    }

    XLOG::l.i("File '{}' was moved successfully to '{}'", source_file,
              destination_file);
    return true;
}

// store file in the folder
// used to save last installed MSI
// no return because we will install new MSI always
void BackupFile(const std::filesystem::path& file_name,
                const std::filesystem::path& backup_dir) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;

    if (backup_dir.empty() || !fs::exists(backup_dir, ec) ||
        !fs::is_directory(backup_dir, ec)) {
        XLOG::l("Backup Path '{}' can't be used", backup_dir);
        return;
    }

    if (file_name.empty() || !cma::tools::IsValidRegularFile(file_name)) {
        XLOG::l("Backup of the '{}' impossible", file_name);
        return;
    }

    auto fname = file_name.filename();
    fs::copy_file(file_name, backup_dir / fname,
                  fs::copy_options::overwrite_existing, ec);
    if (ec.value() != 0) {
        XLOG::l("Backup of the '{}' in '{}' failed with error [{}]", file_name,
                backup_dir, ec.value());
    }

    XLOG::l.i("Backup of the '{}' in '{}' succeeded", file_name, backup_dir);
}

// logic was copy pasted from the cma::cfg::cap::NeedReinstall
// return true when BackupDir is absent, BackupDir/IncomingFile.filename absent
// or when IncomingFile is newer than BackupDir/IncomingFile.filename
// Diagnostic for the "install" case
bool NeedInstall(const std::filesystem::path& incoming_file,
                 const std::filesystem::path& backup_dir) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;

    if (!fs::exists(incoming_file, ec)) {
        XLOG::d.w(
            "Source File '{}' is absent, installation not required and this is strange",
            incoming_file);
        return false;
    }

    if (!fs::exists(backup_dir, ec)) {
        XLOG::l.crit(
            "Target folder '{}' absent, Agent Installation is broken. We try to continue.",
            backup_dir);
        return true;
    }

    // now both file are present
    auto fname = incoming_file.filename();
    auto saved_file = backup_dir / fname;
    if (!fs::exists(saved_file, ec)) {
        XLOG::l.i("First Update in dir {}", backup_dir);
        return true;
    }

    auto target_time = fs::last_write_time(saved_file, ec);
    auto src_time = fs::last_write_time(incoming_file, ec);
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
                log_file_name);
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

namespace {
void BackupLogFile(const std::filesystem::path& log_file_name) {
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
}  // namespace

std::pair<std::wstring, std::wstring> PrepareExecution(
    const std::filesystem::path& exe, const std::filesystem::path& msi,
    bool validate_script_exists) {
    namespace fs = std::filesystem;

    auto [command_tail, log_file_name] = MakeCommandLine(msi);

    std::wstring command;

    fs::path script_file(cfg::GetRootUtilsDir());
    script_file /= cfg::files::kExecuteUpdateFile;
    std::error_code ec;

    // no validate -> new
    // validate and script is present -> new
    // validate and script is absent -> old
    auto required_script_absent =
        validate_script_exists && !fs::exists(script_file, ec);

    if (UseScriptToInstall() && !required_script_absent) {
        fs::path script_log(cfg::GetLogDir());
        script_log /= "execute_script.log";

        command =
            fmt::format(LR"("{}" "{}" "{}" "{}")",
                        script_file.wstring(),  // path/to/execute_update.cmd
                        exe.wstring(),          // path/to/msiexec.exe
                        command_tail,  // "/i check_mk_agent.msi /qn /L*V log"
                        script_log.wstring());  // script.log
    } else {
        command = exe.wstring() + L" " + command_tail;
    }

    XLOG::l.i("File '{}' exists\n\tCommand is '{}'", msi,
              wtools::ToUtf8(command));

    return {command, log_file_name};
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
        XLOG::l.i("Installing '{}'", msi_to_install);
    }

    try {
        const auto [command, log_file_name] =
            PrepareExecution(exe, msi_to_install, true);

        BackupLogFile(log_file_name);

        if (start_update_process == UpdateProcess::skip) {
            XLOG::l.i("Actual Updating is disabled");
            return {command, true};
        }

        return {command, tools::RunStdCommand(command, false, TRUE) != 0};
    } catch (const std::exception& e) {
        XLOG::l("Unexpected exception '{}' during attempt to exec update ",
                e.what());
    }
    { return {{}, false}; }
}

/// \brief - checks that post install flag is set by MSI
///
/// Must be called by any executable to check that installation is finalized
bool IsPostInstallRequired() {
    return std::wstring(registry::kMsiPostInstallRequest) ==
           wtools::GetRegistryValue(registry::GetMsiRegistryPath(),
                                    registry::kMsiPostInstallRequired,
                                    registry::kMsiPostInstallDefault);
}

/// \brief - cleans post install flag
///
/// Normally called only by service after installation Python module
void ClearPostInstallFlag() {
    wtools::SetRegistryValue(registry::GetMsiRegistryPath(),
                             registry::kMsiPostInstallRequired,
                             registry::kMsiPostInstallDefault);
}

/// \brief - checks that migration flag is set by MSI
///
/// Normally called only by service during upgrade config
bool IsMigrationRequired() {
    return std::wstring(registry::kMsiMigrationRequest) ==
           wtools::GetRegistryValue(registry::GetMsiRegistryPath(),
                                    registry::kMsiMigrationRequired,
                                    registry::kMsiMigrationDefault);
}
};  // namespace cma::install
