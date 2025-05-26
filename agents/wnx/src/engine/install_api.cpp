
// install MSI automatic

#include "stdafx.h"

#include "wnx/install_api.h"

#include <msi.h>

#include <filesystem>
#include <fstream>
#include <ranges>
#include <string>

#include "common/wtools.h"   // converts
#include "tools/_process.h"  // start process
#include "wnx/cfg.h"
#include "wnx/cma_core.h"
#include "wnx/logger.h"

#pragma comment(lib, "msi.lib")
namespace fs = std::filesystem;
namespace rs = std::ranges;

namespace cma::install {
bool g_use_script_to_install{true};

namespace {
std::wstring GetMsiProductId(int i) {
    constexpr size_t buf_size{500};
    wchar_t buf[buf_size] = {0};
    return ::MsiEnumProductsW(i, buf) == 0 ? std::wstring{buf} : std::wstring();
}

std::wstring GetMsiProductName(std::wstring_view product_id) {
    constexpr size_t buf_size{500};
    wchar_t product_name[500] = {0};
    DWORD len{buf_size};
    return ::MsiGetProductInfoW(product_id.data(),
                                INSTALLPROPERTY_INSTALLEDPRODUCTNAME,
                                product_name, &len) == 0
               ? std::wstring{product_name}
               : std::wstring();
}

std::wstring GetMsiProductLocalPackage(std::wstring_view product_id) {
    constexpr size_t buf_size{500};
    wchar_t local_package[500] = {0};
    DWORD len{buf_size};
    return ::MsiGetProductInfoW(product_id.data(), INSTALLPROPERTY_LOCALPACKAGE,
                                local_package, &len) == 0
               ? std::wstring{local_package}
               : std::wstring();
}

}  // namespace

std::optional<fs::path> FindProductMsi(std::wstring_view product_name) {
    if (product_name.empty()) {
        XLOG::l("Empty package name");
        return {};
    }

    for (auto i = 0;; ++i) {
        auto product_id = GetMsiProductId(i);
        if (product_id.empty()) {
            break;
        }

        if (GetMsiProductName(product_id) != product_name) {
            continue;
        }

        auto local_package = GetMsiProductLocalPackage(product_id);
        if (local_package.empty()) {
            XLOG::l("Product '{}' found, but error reading local_package",
                    wtools::ToUtf8(product_name));
            return {};
        }

        return {local_package};
    }
    XLOG::d.w("Package not found '{}'", wtools::ToUtf8(product_name));
    return {};
}

bool UseScriptToInstall() noexcept { return g_use_script_to_install; }

InstallMode GetInstallMode() { return InstallMode::normal; }

fs::path MakeTempFileNameInTempPath(std::wstring_view file_name) {
    // Find Temporary Folder
    fs::path temp_folder{tools::win::GetTempFolder()};
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
fs::path GenerateTempFileNameInTempPath(std::wstring_view msi_name) {
    // Find Temporary Folder
    fs::path temp_folder{tools::win::GetTempFolder()};
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
        if (!fs::exists(ret_path, ec) && fs::create_directory(ret_path, ec)) {
            break;
        }

        XLOG::l("Proposed folder exists '{}'", ret_path);
        attempt++;
        if (attempt >= max_attempts) {
            XLOG::l("Can't find free name for folder");
            return {};
        }
    }

    return ret_path / msi_name;
}

static void LogPermissions(const fs::path &file_name) noexcept {
    try {
        auto fname = wtools::ToUtf8(file_name.wstring());
        wtools::ACLInfo acl(fname.c_str());
        auto ret = acl.query();
        if (ret == S_OK) {
            XLOG::l("Permissions:\n{}", acl.output());
        } else {
            XLOG::l("Permission access failed with error {:#X}", ret);
        }
    } catch (const std::exception &e) {
        XLOG::l("Exception hit in bad place {}", e);
    }
}

static bool RmFileWithRename(const fs::path &file_name,
                             std::error_code ec) noexcept {
    XLOG::l(
        "Updating is NOT possible, can't delete file '{}', error [{}]. Trying rename.",
        file_name, ec.value());

    LogPermissions(file_name);
    LogPermissions(file_name.parent_path());

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

namespace {
std::wstring MsiFileToRecoverMsi(const std::wstring &name) {
    return name + L".recover";
}
}  // namespace

// remove file with diagnostic
// for internal use by cma::install
bool RmFile(const fs::path &file_name) noexcept {
    std::error_code ec;
    if (!fs::exists(file_name, ec)) {
        XLOG::l.t("File '{}' is absent, no need to delete", file_name);
        return true;
    }

    if (fs::remove(file_name, ec) || !ec) {  // either deleted or disappeared
        XLOG::l.i("File '{}'was removed", file_name);
        return true;
    }

    return RmFileWithRename(file_name, ec);
}

// MOVE(rename) file with diagnostic
// for internal use by cma::install
bool MvFile(const fs::path &source_file,
            const fs::path &destination_file) noexcept {
    std::error_code ec;
    fs::rename(source_file, destination_file, ec);
    if (ec) {
        XLOG::l("Can't move file '{}' to '{}', error [{}]", source_file,
                destination_file, ec.value());
        return false;
    }

    XLOG::l.i("File '{}' was moved successfully to '{}'", source_file,
              destination_file);
    return true;
}

// store file in the folder
// used to save last installed MSI
// no return because we will install new MSI always
void BackupFile(const fs::path &file_name,
                const fs::path &backup_dir) noexcept {
    std::error_code ec;

    if (backup_dir.empty() || !fs::exists(backup_dir, ec) ||
        !fs::is_directory(backup_dir, ec)) {
        XLOG::l("Backup Path '{}' can't be used", backup_dir);
        return;
    }

    if (file_name.empty() || !tools::IsValidRegularFile(file_name)) {
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
bool NeedInstall(const fs::path &incoming_file,
                 const fs::path &backup_dir) noexcept {
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

    const auto target_time = fs::last_write_time(saved_file, ec);
    const auto src_time = fs::last_write_time(incoming_file, ec);
    return src_time > target_time;
}

/// - checks we have newer file than installed
///
/// In the case of any problems returns true
/// No unit tests
bool NeedInstall(const fs::path &incoming_file) noexcept {
    std::error_code ec;

    if (!fs::exists(incoming_file, ec)) {
        XLOG::d.w(
            "Source File '{}' is absent, installation not required and this is strange",
            incoming_file);
        return false;
    }

    auto installed_msi = FindProductMsi(kAgentProductName);
    if (!installed_msi) {
        XLOG::d.i(
            "Installation not found, this is QUITE strange, assume required");
        return true;
    }

    const auto target_time = fs::last_write_time(*installed_msi, ec);
    if (ec) {
        XLOG::d.w("Can't check data from '{}' assume installation required",
                  *installed_msi);
        return true;
    }
    const auto src_time = fs::last_write_time(incoming_file, ec);
    if (ec) {
        XLOG::d.w("Can't check data from '{}' assume installation required",
                  incoming_file);
        return true;
    }

    return src_time > target_time;
}

std::pair<std::wstring, std::wstring> MakeCommandLine() {
    // msiexecs' parameters below are not fixed unfortunately
    // documentation is scarce and method of installation in MK
    // is not a special standard
    fs::path log_file_name = cfg::GetLogDir();
    std::error_code ec;
    if (!fs::exists(log_file_name, ec)) {
        XLOG::d("Log file path doesn't '{}' exist. Fallback to install.",
                log_file_name);
        log_file_name = cfg::GetUserInstallDir();
    }

    log_file_name /= kMsiLogFileName;

    std::wstring command{L"/qn"};  // but MS doesn't care at all :)

    if (GetInstallMode() == InstallMode::reinstall) {
        // this is REQUIRED when we are REINSTALLING already installed
        // package
        command += L" REINSTALL = ALL REINSTALLMODE = amus";
    }

    command += L" REBOOT=ReallySuppress /L*V ";  // quoting too!
    command += log_file_name;

    return {command, log_file_name.wstring()};
}

void ExecuteUpdate::backupLog() const {
    std::error_code ec;
    fs::path log_file_name{log_file_name_};

    if (!fs::exists(log_file_name, ec)) {
        return;
    }

    XLOG::l.i("Log file '{0}' exists, backing up to '{0}.bak'", log_file_name);

    auto log_bak_file_name = log_file_name;
    log_bak_file_name.replace_extension(".log.bak");

    if (!MvFile(log_file_name, log_bak_file_name)) {
        XLOG::d("Backing up of msi log failed");
    }
}

void ExecuteUpdate::determineFilePaths() {
    base_script_file_ = cfg::GetRootUtilsDir();
    base_script_file_ /= cfg::files::kExecuteUpdateFile;

    temp_script_file_ =
        fs::temp_directory_path() /
        fmt::format("cmk_update_agent_{}", ::GetCurrentProcessId()) /
        cfg::files::kExecuteUpdateFile;
}

bool ExecuteUpdate::copyScriptToTemp() const {
    try {
        fs::create_directories(temp_script_file_.parent_path());
        fs::copy_file(base_script_file_, temp_script_file_,
                      fs::copy_options::overwrite_existing);
        return fs::exists(temp_script_file_);
    } catch (const fs::filesystem_error &e) {
        api_err::Register(
            fmt::format("Failure in copyScriptToTemp '{}' f1= '{}' f2= '{}'",
                        e.what(), e.path1(), e.path2()));
        XLOG::l("Failure in copyScriptToTemp '{}' f1= '{}' f2= '{}'", e.what(),
                e.path1(), e.path2());
    }

    return false;
}

void ExecuteUpdate::prepare(const fs::path &exe, const fs::path &msi,
                            const fs::path &recover_msi,
                            bool validate_script_exists) {
    const auto [command_tail, log_file_name] = MakeCommandLine();
    log_file_name_ = log_file_name;

    std::error_code ec;

    // no validate -> new
    // validate and script is present -> new
    // validate and script is absent -> old
    const auto required_script_absent =
        validate_script_exists && !fs::exists(base_script_file_, ec);

    if (UseScriptToInstall() && !required_script_absent) {
        fs::path script_log(cfg::GetLogDir());
        script_log /= "execute_script.log";

        command_ = fmt::format(
            LR"("{}" "{}" "{}" "{}" "{}" "{}")",
            temp_script_file_.wstring(),  // path/to/execute_update.cmd
            exe.wstring(),                // path/to/msiexec.exe
            command_tail,                 // "/qn /L*V log"
            script_log.wstring(),         // script.log
            msi.wstring(),                // path/to/check_mk_agent.msi
            recover_msi.wstring());       // path/to/recover.msi
    } else {
        command_ = fmt::format(LR"({} /i {} {})",
                               exe.wstring(),  // path/to/msiexec.exe
                               msi.wstring(),  // install
                               command_tail);  // "/qn /L*V log"
    }

    XLOG::l.i("File '{}' exists\n\tCommand is '{}'", msi,
              wtools::ToUtf8(command_));
}

namespace {
/// - returns the recovery file path which may not exist
///
/// Name is based on the msi to be installed with special extension.
/// The file content will be find in the windows install base
/// Never fail.
fs::path CreateRecoveryFile(const fs::path &msi_to_install) {
    auto recover_file = MsiFileToRecoverMsi(msi_to_install);

    if (!RmFile(recover_file)) {
        XLOG::l.i("Fallback to use random name to delete {}",
                  wtools::ToUtf8(recover_file));
        MvFile(recover_file, GenerateTempFileNameInTempPath(recover_file));
    }

    auto installed_msi = FindProductMsi(kAgentProductName);
    if (installed_msi) {
        XLOG::d.i("Product '{}' found, msi is '{}'",
                  wtools::ToUtf8(kAgentProductName), *installed_msi);
        std::error_code ec;
        fs::copy_file(*installed_msi, recover_file,
                      fs::copy_options::overwrite_existing, ec);
    } else {
        XLOG::l("The product '{}' not found, this is not normal situation",
                wtools::ToUtf8(kAgentProductName));
    }

    return recover_file;
}

/// - delivers msi to be installed in temp
///
/// Move MSI to be installed into temp
/// May fail. On fail caller should stop installation.
std::optional<fs::path> CreateInstallFile(const fs::path &msi_base,
                                          std::wstring_view msi_name) {
    auto msi_to_install = MakeTempFileNameInTempPath(msi_name);
    if (msi_to_install.empty()) {
        return {};
    }

    if (RmFile(msi_to_install)) {
        if (!MvFile(msi_base, msi_to_install)) {
            return {};
        }
    } else {
        // THIS BRANCH TESTED MANUALLY
        XLOG::l.i("Fallback to use random name");
        auto temp_name = GenerateTempFileNameInTempPath(msi_name);
        if (temp_name.empty()) {
            return {};
        }
        if (!MvFile(msi_base, temp_name)) {
            return {};
        }

        msi_to_install = temp_name;
        XLOG::l.i("Installing '{}'", msi_to_install);
    }
    return msi_to_install;
}
}  // namespace

// check that update exists and exec it
// returns true when update found and ready to exec
std::pair<std::wstring, bool> CheckForUpdateFile(
    std::wstring_view msi_name, std::wstring_view msi_dir,
    UpdateProcess start_update_process) {
    // find path to msiexec, in Windows it is in System32 folder
    const auto exe = cfg::GetMsiExecPath();
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

    if (!NeedInstall(msi_base)) {
        fs::path skip_file = msi_base;
        skip_file += ".skip";
        RmFile(skip_file);
        MvFile(msi_base, skip_file);
        return {{}, false};
    }

    api_err::Clean();

    auto msi_to_install = CreateInstallFile(msi_base, msi_name);
    if (!msi_to_install) {
        api_err::Register("Impossible to copy MSI, please, check log file");
        return {{}, false};
    }

    auto recover_file = CreateRecoveryFile(*msi_to_install);

    try {
        ExecuteUpdate eu;
        eu.prepare(exe, *msi_to_install, recover_file, true);
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
        return {command,
                tools::RunStdCommand(command, tools::WaitForEnd::no) != 0};
    } catch (const std::exception &e) {
        auto log_text = fmt::format(
            "Unexpected exception '{}' during attempt to execute agent update",
            e.what());
        api_err::Register(log_text);
        XLOG::l(log_text);
    }
    return {{}, false};
}

/// - checks that post install flag is set by MSI
///
/// Must be called by any executable to check that installation is finalized
bool IsPostInstallRequired() {
    return std::wstring(registry::kMsiPostInstallRequest) ==
           wtools::GetRegistryValue(registry::GetMsiRegistryPath(),
                                    registry::kMsiPostInstallRequired,
                                    registry::kMsiPostInstallDefault);
}

/// - cleans post install flag
///
/// Normally called only by service after installation Python module
void ClearPostInstallFlag() {
    wtools::SetRegistryValue(registry::GetMsiRegistryPath(),
                             registry::kMsiPostInstallRequired,
                             registry::kMsiPostInstallDefault);
}

/// - checks that clean install flag is set by MSI
///
/// Must be called by any executable to check that installation is finalized
bool IsCleanInstallationRequired() {
    return std::wstring(registry::kMsiCleanInstallationlRequest) ==
           wtools::GetRegistryValue(registry::GetMsiRegistryPath(),
                                    registry::kMsiCleanInstallationEntry, L"");
}

/// - remove clean install flag
///
/// Normally called only by service after installation Python module
void RemoveCleanInstallationFlag() {
    wtools::SetRegistryValue(registry::GetMsiRegistryPath(),
                             registry::kMsiCleanInstallationEntry, L"");
}

/// - checks that migration flag is set by MSI
///
/// Normally called only by service during upgrade config
bool IsMigrationRequired() {
    return std::wstring(registry::kMsiMigrationRequest) ==
           wtools::GetRegistryValue(registry::GetMsiRegistryPath(),
                                    registry::kMsiMigrationRequired,
                                    registry::kMsiMigrationDefault);
}

namespace {
std::optional<fs::path> FindMsiLog() {
    auto msi_log_file = fs::path{cfg::GetLogDir()} / kMsiLogFileName;
    std::error_code ec;
    if (!fs::exists(msi_log_file, ec)) {
        return {};
    }

    return {msi_log_file};
}

std::optional<fs::path> FindInstallApiLog() {
    auto install_api_log_file =
        fs::path{cfg::GetLogDir()} / api_err::kLogFileName;
    std::error_code ec;
    if (!fs::exists(install_api_log_file, ec)) {
        return {};
    }

    return {install_api_log_file};
}

auto ReadFileAsTable(const fs::path &name) {
    std::ifstream in(wtools::ToUtf8(name.wstring()));
    std::stringstream sstr;
    sstr << in.rdbuf();
    return tools::SplitString(sstr.str(), "\n");
}

/// reads the file which must be encoded as LE BOM
std::wstring ReadLeBom(const fs::path &file) {
    constexpr size_t max_log_size{8192U * 1024U};
    constexpr auto ff = static_cast<unsigned char>('\xFF');
    constexpr auto fe = static_cast<unsigned char>('\xFE');
    constexpr std::array le_bom_marker{ff, fe};
    try {
        std::ifstream f1(file, std::ifstream::binary | std::ifstream::ate);

        const auto size = static_cast<size_t>(f1.tellg());
        if (size > max_log_size) {
            return {};
        }
        f1.seekg(0, std::ifstream::beg);
        std::array<unsigned char, 2> buf{0, 0};
        f1.read(reinterpret_cast<char *>(buf.data()), buf.size());
        if (buf != le_bom_marker) {
            XLOG::l(
                "Expected LE BOM file {}, but at the start we have '{:X} {:X}'",
                file, static_cast<unsigned int>(buf[0]),
                static_cast<unsigned int>(buf[1]));
            return {};
        }
        std::wstring ret;
        ret.resize(size - 2);
        f1.read(reinterpret_cast<char *>(ret.data()), size - 2);
        return ret;

    } catch (const std::exception &e) {
        XLOG::l("Error during attempt to read LE BOM file {}", e.what());
    }
    return {};
}

std::vector<std::wstring> FindStringsByMarker(const std::wstring &content,
                                              const std::wstring &marker) {
    std::vector<std::wstring> strings;
    size_t cur_offset = 0;
    while (true) {
        const auto offset = content.find(marker, cur_offset);
        if (offset == std::wstring::npos) {
            break;
        }
        const auto end = content.find(L"\r\n", offset);
        if (end == std::wstring::npos) {
            strings.emplace_back(content.substr(offset));
        } else if (offset != end) {
            strings.emplace_back(content.substr(offset, end - offset));
        }
        cur_offset = offset + 1;
    }

    return strings;
}

std::wstring ExpectedMarker() {
    static const auto product_marker =
        fmt::format(L"Product: {}", kAgentProductName);
    return product_marker;
}

void DeleteInstallApiLog() {
    if (auto log_file = FindInstallApiLog()) {
        fs::path bak_file = *log_file;
        bak_file += ".bak";  // backing up is always useful
        RmFile(bak_file);
        MvFile(*log_file, bak_file);
    }
}

}  // namespace

std::optional<std::wstring> GetLastMsiFailReason() {
    const auto msi_log = FindMsiLog();
    if (!msi_log) {
        return {};
    }
    const auto content = ReadLeBom(*msi_log);
    const auto product_strings = FindStringsByMarker(content, ExpectedMarker());
    if (rs::any_of(product_strings, [](const std::wstring &value) {
            return value.find(L"Installation failed") != std::wstring::npos;
        })) {
        return {product_strings[0]};
    }
    return {};
}

namespace api_err {
std::optional<std::wstring> Get() {
    const auto api_log = FindInstallApiLog();
    if (!api_log) {
        return {};
    }
    for (const auto &line : ReadFileAsTable(*api_log)) {
        if (line.starts_with(api_err::kFailMarker)) {
            return wtools::ConvertToUtf16(line.c_str() +
                                          api_err::kFailMarker.length());
        }
    }

    return {};
}

void Register(const std::string &error) {
    DeleteInstallApiLog();
    std::ofstream ofs(fs::path{cfg::GetLogDir()} / api_err::kLogFileName,
                      std::ios::trunc);
    ofs << api_err::kFailMarker << error << "\n";
}

void Clean() { DeleteInstallApiLog(); }
}  // namespace api_err

}  // namespace cma::install
