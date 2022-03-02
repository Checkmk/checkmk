// Windows Tools
#include "stdafx.h"

#include "upgrade.h"

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>

#include "common/yaml.h"
#include "cvt.h"
#include "glob_match.h"
#include "install_api.h"
#include "logger.h"
#include "providers/ohm.h"
#include "tools/_misc.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::cfg::upgrade {

// SERVICE_AUTO_START : SERVICE_DISABLED
enum class ServiceStartType {
    disable = SERVICE_DISABLED,
    auto_start = SERVICE_AUTO_START

};

// returns false if folder cannot be created
[[nodiscard]] bool CreateFolderSmart(
    const std::filesystem::path &tgt) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (cma::tools::IsValidRegularFile(tgt)) fs::remove(tgt, ec);
    if (fs::exists(tgt, ec)) return true;

    auto ret = fs::create_directories(tgt, ec);
    // check created or already exists
    if (ret || ec.value() == 0) return true;

    XLOG::l("Can't create '{}' error = [{}]", tgt, ec.value());
    return false;
}

bool IsPathProgramData(const std::filesystem::path &program_data) {
    std::filesystem::path mask = kAppDataCompanyName;
    mask /= kAppDataAppName;
    std::wstring mask_str = mask.wstring();
    cma::tools::WideLower(mask_str);

    auto test_path = program_data.lexically_normal().native();
    cma::tools::WideLower(test_path);

    return test_path.find(mask_str) != std::wstring::npos;
}

[[nodiscard]] bool IsFileNonCompatible(
    const std::filesystem::path &fname) noexcept {
    constexpr std::string_view forbidden_files[] = {"cmk-update-agent.exe"};

    auto name = fname.filename();

    auto text = name.u8string();
    cma::tools::StringLower(text);

    return std::any_of(std::begin(forbidden_files), std::end(forbidden_files),
                       // predicate:
                       [text](std::string_view file) { return file == text; }

    );
}

int CopyAllFolders(const std::filesystem::path &legacy_root,
                   const std::filesystem::path &program_data,
                   CopyFolderMode copy_mode) {
    namespace fs = std::filesystem;
    if (!IsPathProgramData(program_data)) {
        XLOG::d(XLOG_FUNC + " '{}' is bad folder, copy is not possible",
                program_data);
        return 0;
    }

    static const std::wstring_view folders[] = {
        L"config", L"plugins", L"local",
        L"spool",  // may contain important files
        L"mrpe",   L"state",   L"bin"};

    auto count = 0;
    for_each(folders, std::end(folders),

             [legacy_root, program_data, &count,
              copy_mode](std::wstring_view sub_folder) {
                 auto src = legacy_root / sub_folder;
                 auto tgt = program_data / sub_folder;
                 XLOG::l.t("Processing '{}', mode [{}]:", src,
                           static_cast<int>(copy_mode));  //
                 if (copy_mode == CopyFolderMode::remove_old)
                     fs::remove_all(tgt);
                 auto folder_exists = CreateFolderSmart(tgt);
                 if (!folder_exists) return;

                 auto c = CopyFolderRecursive(
                     src, tgt, fs::copy_options::skip_existing, [](fs::path p) {
                         XLOG::l.i("\tCopy '{}'", p);
                         return true;
                     });
                 count += c;
             });

    return count;
}

namespace details {

constexpr const std::string_view ignored_exts[] = {".ini", ".exe", ".log",
                                                   ".tmp"};

constexpr const std::string_view ignored_names[] = {
    "plugins.cap",
};

// single point entry to determine that file is ignored
bool IsIgnoredFile(const std::filesystem::path &filename) {
    using namespace cma::tools;

    // check extension
    auto extension = filename.extension();
    auto extension_string = extension.u8string();
    StringLower(extension_string);

    for (auto ext : ignored_exts)
        if (ext == extension_string) return true;

    // check name
    auto fname = filename.filename().u8string();
    StringLower(fname);

    for (auto name : ignored_names)
        if (fname == name) return true;

    // check mask
    std::string mask = "uninstall_*.bat";
    if (GlobMatch(mask, fname)) return true;

    return false;
}
}  // namespace details

// copies all files from root, exception is ini and exe
// returns count of files copied
int CopyRootFolder(const std::filesystem::path &LegacyRoot,
                   const std::filesystem::path &ProgramData) {
    namespace fs = std::filesystem;
    using namespace cma::tools;
    using namespace cma::cfg;

    auto count = 0;
    std::error_code ec;
    for (const auto &dir_entry : fs::directory_iterator(LegacyRoot, ec)) {
        const auto &p = dir_entry.path();
        if (fs::is_directory(p, ec)) continue;

        if (details::IsIgnoredFile(p)) {
            XLOG::l.i("File '{}' in root folder '{}' is ignored", p,
                      LegacyRoot);
            continue;
        }

        // Copy to the targetParentPath which we just created.
        fs::copy(p, ProgramData, fs::copy_options::skip_existing, ec);

        if (ec.value() == 0) {
            count++;
            continue;
        }

        XLOG::l("during copy from '{}' to '{}' error {}", p,
                wtools::ToUtf8(cma::cfg::GetUserDir()), ec.value());
    }

    return count;
}

// Recursively copies those files and folders from src to target which matches
// predicate, and overwrites existing files in target.
int CopyFolderRecursive(
    const std::filesystem::path &source, const std::filesystem::path &target,
    std::filesystem::copy_options copy_mode,
    const std::function<bool(std::filesystem::path)> &predicate) noexcept {
    namespace fs = std::filesystem;
    int count = 0;
    XLOG::l.t("Copy from '{}' to '{}'", source, target);

    try {
        std::error_code ec;
        for (const auto &dir_entry :
             fs::recursive_directory_iterator(source, ec)) {
            const auto &p = dir_entry.path();
            if (predicate(p)) {
                // Create path in target, if not existing.
                const auto relative_src = fs::relative(p, source);
                const auto target_parent_path = target / relative_src;
                if (fs::is_directory(p)) {
                    fs::create_directories(target_parent_path, ec);
                    if (ec.value() != 0) {
                        XLOG::l("Failed create folder '{} error {}",
                                target_parent_path, ec.value());
                        continue;
                    }
                } else {
                    if (IsFileNonCompatible(p)) {
                        XLOG::l.i("File '{}' is skipped as not compatible", p);
                        continue;
                    }

                    // Copy to the targetParentPath which we just created.
                    auto ret =
                        fs::copy_file(p, target_parent_path, copy_mode, ec);
                    if (ec.value() == 0) {
                        if (ret) count++;
                        continue;
                    }
                    XLOG::l("during copy from '{}' to '{}' error {}", p,
                            target_parent_path, ec.value());
                }
            }
        }
    } catch (std::exception &e) {
        XLOG::l("Exception during copy file {}", e.what());
    }

    return count;
}

int GetServiceStatus(SC_HANDLE ServiceHandle) {
    DWORD bytes_needed = 0;
    SERVICE_STATUS_PROCESS ssp;
    auto buffer = reinterpret_cast<LPBYTE>(&ssp);

    if (FALSE == QueryServiceStatusEx(ServiceHandle, SC_STATUS_PROCESS_INFO,
                                      buffer, sizeof(SERVICE_STATUS_PROCESS),
                                      &bytes_needed)) {
        XLOG::l("QueryServiceStatusEx failed [{}]", GetLastError());
        return -1;
    }
    return ssp.dwCurrentState;
}

uint32_t GetServiceHint(SC_HANDLE ServiceHandle) {
    DWORD bytes_needed = 0;
    SERVICE_STATUS_PROCESS ssp;
    auto buffer = reinterpret_cast<LPBYTE>(&ssp);

    if (FALSE == QueryServiceStatusEx(ServiceHandle, SC_STATUS_PROCESS_INFO,
                                      buffer, sizeof(SERVICE_STATUS_PROCESS),
                                      &bytes_needed)) {
        XLOG::l("QueryServiceStatusEx failed [{}]", GetLastError());
        return 0;
    }
    return ssp.dwWaitHint;
}

int SendServiceCommand(SC_HANDLE Handle, uint32_t Command) {
    SERVICE_STATUS_PROCESS ssp;
    if (FALSE == ::ControlService(Handle, Command,
                                  reinterpret_cast<LPSERVICE_STATUS>(&ssp))) {
        XLOG::l("ControlService command [{}] failed [{}]", Command,
                GetLastError());
        return -1;
    }
    return ssp.dwCurrentState;
}

std::tuple<SC_HANDLE, SC_HANDLE, DWORD> OpenServiceForControl(
    std::wstring_view service_name) {
    auto manager_handle =
        ::OpenSCManager(nullptr,                 // local computer
                        nullptr,                 // ServicesActive database
                        SC_MANAGER_ALL_ACCESS);  // full access rights

    if (nullptr == manager_handle) {
        auto error = ::GetLastError();
        XLOG::l("OpenSCManager failed [{}]", error);
        return {nullptr, nullptr, error};
    }

    // Get a handle to the service.

    auto handle =
        ::OpenService(manager_handle,       // SCM database
                      service_name.data(),  // name of service
                      SERVICE_STOP | SERVICE_START | SERVICE_QUERY_STATUS |
                          SERVICE_ENUMERATE_DEPENDENTS);

    if (nullptr == handle) {
        auto error = ::GetLastError();
        XLOG::l("OpenService '{}' failed [{}]", wtools::ToUtf8(service_name),
                error);
        return {manager_handle, handle, error};
    }

    return {manager_handle, handle, 0};
}

int GetServiceStatusByName(const std::wstring &Name) {
    auto [manager_handle, handle, err] = OpenServiceForControl(Name);

    ON_OUT_OF_SCOPE(if (manager_handle) CloseServiceHandle(manager_handle));
    ON_OUT_OF_SCOPE(if (handle) CloseServiceHandle(handle));

    if (nullptr == handle) return err;

    return GetServiceStatus(handle);
}

// from MS MSDN
static uint32_t CalcDelay(SC_HANDLE handle) noexcept {
    auto hint = GetServiceHint(handle);
    // Do not wait longer than the wait hint. A good interval is
    // one-tenth of the wait hint but not less than 1 second
    // and not more than 10 seconds.
    auto delay = hint / 10;
    if (delay < 1000)
        delay = 1000;
    else if (delay > 10000)
        delay = 10000;
    return delay;
}

// internal function based om MS logic from the MSDN, and the logic is not a
// so good as for 2019
static bool TryStopService(SC_HANDLE handle, const std::string &name_to_log,
                           DWORD current_status) noexcept {
    auto status = current_status;
    auto delay = CalcDelay(handle);
    constexpr DWORD timeout = 30000;  // 30-second time-out
    DWORD start_time = GetTickCount();
    // If a stop is pending, wait for it.
    if (status == SERVICE_STOP_PENDING) {
        XLOG::l.i("Service stop pending...");

        while (status == SERVICE_STOP_PENDING) {
            cma::tools::sleep(delay);

            status = GetServiceStatus(handle);

            if (status == -1) return false;

            if (status == SERVICE_STOPPED) {
                XLOG::l.i("Service '{}' stopped successfully.", name_to_log);
                return true;
            }

            if (GetTickCount() - start_time > timeout) {
                XLOG::l("Service stop timed out during pending");
                return false;
            }
        }
    }

    // Send a stop code to the service.
    status = SendServiceCommand(handle, SERVICE_CONTROL_STOP);

    if (status == -1) return false;

    // Wait for the service to stop.

    while (status != SERVICE_STOPPED) {
        cma::tools::sleep(delay);

        status = GetServiceStatus(handle);
        if (status == -1) return false;

        if (GetTickCount() - start_time > timeout) {
            XLOG::l("Wait timed out for '{}'", name_to_log);
            return false;
        }
    }

    XLOG::l.i("Service '{}' really stopped", name_to_log);

    return true;
}

bool StopWindowsService(std::wstring_view service_name) {
    auto name_to_log = wtools::ToUtf8(service_name);
    XLOG::l.t("Service {} stopping ...", name_to_log);

    // Get a handle to the SCM database.
    auto [manager_handle, handle, error] = OpenServiceForControl(service_name);
    ON_OUT_OF_SCOPE(if (manager_handle) CloseServiceHandle(manager_handle));
    ON_OUT_OF_SCOPE(if (handle) CloseServiceHandle(handle));
    if (nullptr == handle) {
        XLOG::l("Cannot open service '{}' with error [{}]", name_to_log, error);
        return false;
    }

    // Make sure the service is not already stopped.
    auto status = GetServiceStatus(handle);
    if (status == -1) return false;

    if (status == SERVICE_STOPPED) {
        XLOG::l.i("Service '{}' is already stopped.", name_to_log);
        return true;
    }

    return TryStopService(handle, name_to_log, status);
}

static void LogStartStatus(const std::wstring &service_name,
                           DWORD last_error_code) {
    auto name = wtools::ToUtf8(service_name);
    if (last_error_code == 0) {
        XLOG::l.i("Service '{}' started successfully ", name);
        return;
    }

    if (last_error_code == 1056) {
        XLOG::l.t("Service '{}' already started [1056]", name);
        return;
    }
    XLOG::l("Service '{}' start failed [{}]", name, last_error_code);
}

bool StartWindowsService(const std::wstring &service_name) {
    // Get a handle to the SCM database.
    auto [manager_handle, handle, error] = OpenServiceForControl(service_name);
    ON_OUT_OF_SCOPE(if (manager_handle) CloseServiceHandle(manager_handle));
    ON_OUT_OF_SCOPE(if (handle) CloseServiceHandle(handle));

    if (nullptr == handle) {
        XLOG::l("Cannot open service '{}' with error [{}]",
                wtools::ToUtf8(service_name), error);
        return false;
    }

    // Make sure the service is not already started
    auto status = GetServiceStatus(handle);
    if (status == -1) return false;  // trash

    if (status == SERVICE_RUNNING) {
        XLOG::l.i("Service is already running.");
        return true;
    }

    if (status != SERVICE_STOPPED) {
        XLOG::l.i(
            "Service is in strange mode = [{}]. This is not a problem, just Windows Feature",
            status);
        // use hammer
        wtools::KillProcessFully(service_name + L".exe", 1);
    }

    // Send a start code to the service.
    auto ret = ::StartService(handle, 0, nullptr);
    LogStartStatus(service_name, ret == TRUE ? 0 : ::GetLastError());

    return true;
}

bool WinServiceChangeStartType(const std::wstring &name,
                               ServiceStartType start_type) {
    auto manager_handle = ::OpenSCManager(nullptr, nullptr, SC_MANAGER_CONNECT);
    if (manager_handle == nullptr) {
        XLOG::l.crit("Cannot open SC MAnager {}", GetLastError());
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(manager_handle));

    auto handle =
        ::OpenService(manager_handle, name.c_str(), SERVICE_CHANGE_CONFIG);
    if (handle == nullptr) {
        XLOG::l.crit("Cannot open Service {}, error =  {}",
                     wtools::ToUtf8(name), GetLastError());
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(handle));

    auto result = ::ChangeServiceConfig(
        handle,                          // handle of service
        SERVICE_NO_CHANGE,               // service type: no change
        static_cast<DWORD>(start_type),  // service start type
        SERVICE_NO_CHANGE,               // error control: no change
        nullptr,                         // binary path: no change
        nullptr,                         // load order group: no change
        nullptr,                         // tag ID: no change
        nullptr,                         // dependencies: no change
        nullptr,                         // account name: no change
        nullptr,                         // password: no change
        nullptr);                        // display name: no change
    if (result == 0) {
        XLOG::l("ChangeServiceConfig '{}' failed [{}]", wtools::ToUtf8(name),
                GetLastError());
        return false;
    }

    return true;
}

// testing block
// used only during unit testing
std::filesystem::path G_LegacyAgentPresetPath;
void SetLegacyAgentPath(const std::filesystem::path &path) {
    G_LegacyAgentPresetPath = path;
}

std::wstring FindLegacyAgent() {
    if (!G_LegacyAgentPresetPath.empty()) return G_LegacyAgentPresetPath;

    namespace fs = std::filesystem;
    auto image_path = wtools::GetRegistryValue(
        L"SYSTEM\\CurrentControlSet\\Services\\check_mk_agent", L"ImagePath",
        L"");

    if (image_path.empty()) return {};

    // remove double quotes
    if (image_path.back() == L'\"') image_path.pop_back();
    auto path = image_path.c_str();
    if (*path == L'\"') ++path;

    fs::path p = path;
    if (!cma::tools::IsValidRegularFile(p)) {
        XLOG::d(
            "Agent is found in registry '{}', but absent on the disk."
            "Assuming that agent is NOT installed",
            p.u8string());
        return {};
    }

    return p.parent_path().wstring();
}

bool IsLegacyAgentActive() {
    auto path = FindLegacyAgent();
    if (path.empty()) return false;

    namespace fs = std::filesystem;
    auto service_type = wtools::GetRegistryValue(
        L"SYSTEM\\CurrentControlSet\\Services\\check_mk_agent", L"StartType",
        SERVICE_DISABLED);
    return service_type != SERVICE_DISABLED;
}

bool ActivateLegacyAgent() {
    wtools::SetRegistryValue(
        L"SYSTEM\\CurrentControlSet\\Services\\check_mk_agent", L"StartType",
        SERVICE_AUTO_START);
    return WinServiceChangeStartType(L"check_mk_agent",
                                     ServiceStartType::auto_start);
}
bool DeactivateLegacyAgent() {
    wtools::SetRegistryValue(
        L"SYSTEM\\CurrentControlSet\\Services\\check_mk_agent", L"StartType",
        SERVICE_DISABLED);
    return WinServiceChangeStartType(L"check_mk_agent",
                                     ServiceStartType::disable);
}

int WaitForStatus(std::function<int(const std::wstring &)> StatusChecker,
                  std::wstring_view ServiceName, int ExpectedStatus, int Time) {
    int status = -1;
    while (true) {
        status = StatusChecker(std::wstring(ServiceName));
        if (status == ExpectedStatus) return status;
        if (Time >= 0) {
            cma::tools::sleep(1000);
            XLOG::l.i("1 second is over status is {}, t=required {}...", status,
                      ExpectedStatus);
        } else
            break;
        Time -= 1000;
    }

    return status;
}

static void LogAndDisplayErrorMessage(int status) {
    auto driver_body =
        cma::cfg::details::FindServiceImagePath(L"winring0_1_2_0");

    using namespace xlog::internal;
    if (!driver_body.empty()) {
        xlog::sendStringToStdio("Probably you have : ", Colors::green);
        XLOG::l.crit("Failed to stop kernel legacy driver winring0_1_2_0 [{}]",
                     status);
        return;
    }

    if (status == SERVICE_STOP_PENDING) {
        XLOG::l.crit(
            "Can't stop windows kernel driver 'winring0_1_2_0', integral part of Open Hardware Monitor\n"
            "'winring0_1_2_0' registry entry is absent, but driver is running having 'SERVICE_STOP_PENDING' state\n"
            "THIS IS ABNORMAL. You must REBOOT Windows. And repeat action.");
        return;
    }

    // this may be ok
    xlog::sendStringToStdio("This is just info: ", Colors::green);
    XLOG::l.w(
        "Can't stop winring0_1_2_0 [{}], probably you have no 'Open Hardware Monitor' running.",
        status);
}

bool FindStopDeactivateLegacyAgent() {
    XLOG::l.t("Find, stop and deactivate");
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(
            "You have to be in elevated to use this function.\nPlease, run as Administrator");
        return false;
    }
    namespace fs = std::filesystem;
    auto path = FindLegacyAgent();
    if (path.empty()) {
        XLOG::l.t("There is no legacy Check Mk agent installed");
        return true;
    }

    XLOG::l.t("Stopping check_mk_agent...");
    auto ret = StopWindowsService(L"check_mk_agent");
    if (!ret) {
        XLOG::l.crit("Failed to stop check_mk_agent");
        if (!wtools::KillProcessFully(L"check_mk_agent.exe", 9)) return false;
    }

    XLOG::l.t("Checking check_mk_agent status...");
    auto status = GetServiceStatusByName(L"check_mk_agent");
    if (status != SERVICE_STOPPED) {
        XLOG::l.crit("Wrong status of check_mk_agent {}", status);
        return false;
    }

    XLOG::l.t("Deactivate check_mk_agent ...");
    DeactivateLegacyAgent();
    if (IsLegacyAgentActive()) {
        XLOG::l.crit("Failed to deactivate check_mk_agent");
        return false;
    }

    XLOG::l.t("Killing open hardware monitor...");
    wtools::KillProcess(cma::provider::ohm::kExeModuleWide, 1);
    wtools::KillProcess(cma::provider::ohm::kExeModuleWide,
                        1);  // we may have two :)

    XLOG::l.t("Stopping winring0_1_2_0...");
    StopWindowsService(L"winring0_1_2_0");
    status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                           SERVICE_STOPPED, 5000);

    if (status == SERVICE_STOPPED) return true;
    if (status == 1060) return true;  // case when driver killed by OHM

    // below we have variants when damned OHM kill and remove damned
    // driver before we have a chance to check its stop
    if (status == 1060) return true;
    if (status == -1) return true;

    LogAndDisplayErrorMessage(status);

    return false;
}

static bool RunOhm(const std::filesystem::path &lwa_path) noexcept {
    namespace fs = std::filesystem;
    fs::path ohm = lwa_path;
    ohm /= "bin";
    ohm /= "OpenHardwareMonitorCLI.exe";
    std::error_code ec;
    if (!fs::exists(ohm, ec)) {
        XLOG::l.crit(
            "OpenHardwareMonitor not installed,"
            "please, add it to the Legacy Agent folder");
        return false;
    }

    XLOG::l.t("Starting open hardware monitor...");
    RunDetachedProcess(ohm.wstring());
    WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0", SERVICE_RUNNING,
                  5000);
    return true;
}

bool FindActivateStartLegacyAgent(AddAction action) {
    XLOG::l.t("Find, activate and start");
    namespace fs = std::filesystem;
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(
            "You have to be in elevated to use this function.\nPlease, run as Administrator");
        return false;
    }

    auto path = FindLegacyAgent();
    if (path.empty()) {
        XLOG::l.t("There is no legacy Check Mk agent installed");
        return true;
    }

    XLOG::l.t("Activating check_mk_agent...");
    ActivateLegacyAgent();
    if (!IsLegacyAgentActive()) {
        XLOG::l.crit("Failed to Activate check_mk_agent");
        return false;
    }

    XLOG::l.t("Starting check_mk_agent...");
    auto ret = StartWindowsService(L"check_mk_agent");
    if (!ret) {
        XLOG::l.crit("Failed to stop check_mk_agent");
        return false;
    }

    XLOG::l.t("Checking check_mk_agent...");
    auto status = WaitForStatus(GetServiceStatusByName, L"check_mk_agent",
                                SERVICE_RUNNING, 5000);
    if (status != SERVICE_RUNNING) {
        XLOG::l.crit("Wrong status of check_mk_agent {}", status);
        return false;
    }

    // mostly for test and security
    if (action == AddAction::start_ohm) RunOhm(path);

    return true;
}

bool RunDetachedProcess(const std::wstring &Name) {
    // start process
    STARTUPINFO si;
    PROCESS_INFORMATION pi;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    std::wstring name = Name;
    auto windows_name = const_cast<LPWSTR>(name.c_str());

    auto ret = CreateProcessW(
        nullptr,       // application name
        windows_name,  // Command line options
        nullptr,       // Process handle not inheritable
        nullptr,       // Thread handle not inheritable
        FALSE,         // Set handle inheritance to FALSE
        CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,  // No creation flags
        nullptr,  // Use parent's environment block
        nullptr,  // Use parent's starting directory
        &si,      // Pointer to STARTUPINFO structure
        &pi);     // Pointer to PROCESS_INFORMATION structure
    if (ret != TRUE) {
        XLOG::l("Cant start the process {}, error is {}", wtools::ToUtf8(Name),
                GetLastError());
    }
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return ret == TRUE;
}

std::filesystem::path ConstructProtocolFileName(
    const std::filesystem::path &dir) noexcept {
    namespace fs = std::filesystem;
    fs::path protocol_file = dir;
    protocol_file /= cma::cfg::files::kUpgradeProtocol;
    return protocol_file;
}

bool CreateProtocolFile(const std::filesystem::path &dir,
                        std::string_view OptionalContent) {
    try {
        auto protocol_file = ConstructProtocolFileName(dir);
        std::ofstream ofs(protocol_file, std::ios::binary);

        if (ofs) {
            ofs << "Upgraded:\n";
            ofs << "  time: '" << cma::cfg::ConstructTimeString() << "'\n";
            if (!OptionalContent.empty()) {
                ofs << OptionalContent;
                ofs << "\n";
            }
        }
    } catch (const std::exception &e) {
        XLOG::l.crit("Exception during creatin protocol file {}", e.what());
        return false;
    }
    return true;
}

bool IsProtocolFileExists(const std::filesystem::path &root_folder) {
    namespace fs = std::filesystem;
    auto protocol_file = ConstructProtocolFileName(root_folder);
    std::error_code ec;

    return fs::exists(protocol_file, ec);
}

static void InfoOnStdio(bool force) {
    if (!force) return;

    XLOG::SendStringToStdio("Upgrade(migration) is forced by command line\n",
                            XLOG::Colors::yellow);
}

// manually tested
// may be removed
// just to support old betas location of protocol.upgrade
bool UpdateProtocolFile(std::wstring_view new_location,
                        std::wstring_view old_location) {
    if (new_location == old_location) return false;

    namespace fs = std::filesystem;
    auto old_protocol_file_exists = IsProtocolFileExists(old_location);
    auto new_protocol_file_exists = IsProtocolFileExists(new_location);

    std::error_code ec;
    if (new_protocol_file_exists && old_protocol_file_exists) {
        fs::remove(ConstructProtocolFileName(old_location), ec);
        XLOG::d("Manipulation with old protocol file:remove");
        return true;
    }

    if (old_protocol_file_exists) {
        fs::rename(ConstructProtocolFileName(old_location),
                   ConstructProtocolFileName(new_location), ec);
        XLOG::d("Manipulation with old protocol file:rename");
    }
    return true;
}

std::filesystem::path ConstructDatFileName() noexcept {
    namespace fs = std::filesystem;
    fs::path dat = GetRootDir();
    dat /= dirs::kFileInstallDir;
    dat /= files::kDatFile;
    return dat;
}

std::filesystem::path FindOwnDatFile() {
    namespace fs = std::filesystem;
    auto dat = ConstructDatFileName();
    std::error_code ec;
    if (fs::exists(dat, ec)) return dat;
    XLOG::l("dat files should be located at '{}'", dat);
    return {};
}

static std::filesystem::path GetHashedIniName() {
    auto ini = FindOldIni();
    if (ini.empty()) {
        XLOG::l.t("INI file not found, patching is not required");
        return {};
    }

    auto old_ini_hash = GetOldHashFromIni(ini);
    if (old_ini_hash.empty()) {
        XLOG::l.t("Hash in INI file '{}' not found, patching is not required",
                  ini);
        return {};
    }

    XLOG::l.t("Patching of the ini '{}' initiated, old hash is '{}' ", ini,
              old_ini_hash);
    return ini;
}

static std::string GetNewHash() {
    auto dat = FindOwnDatFile();
    if (dat.empty()) {
        XLOG::l("DAT file '{}' absent, this is bad", dat);
        return {};
    }

    auto new_hash = GetNewHash(dat);
    if (new_hash.empty()) {
        XLOG::l("Hash in DAT file '{} absent, this is bad too", dat);
        return {};
    }

    return new_hash;
}

static std::filesystem::path GetHashedStateName() {
    auto state = FindOldState();
    if (state.empty()) {
        XLOG::l.t("State file not found, patching is not required");
        return {};
    }

    auto old_state_hash = GetOldHashFromState(state);
    if (old_state_hash.empty()) {
        XLOG::l.t("Hash in State file '{}' not found, patching is not required",
                  state);
        return {};
    }

    XLOG::l.t("Patching of the state '{}' initiated, old hash is '{}' ", state,
              old_state_hash);
    return state;
}

// This Function writes new hash from the dat
// into old ini file to prevent further updates with 1.5 cmk-update-agent.exe
bool PatchOldFilesWithDatHash() {
    namespace fs = std::filesystem;
    auto ini = GetHashedIniName();
    auto state = GetHashedStateName();
    if (ini.empty() || state.empty()) {
        XLOG::l.i("NO NEED TO PATCH!");
        return false;
    }

    auto new_hash = GetNewHash();
    if (new_hash.empty()) return false;

    XLOG::t("Hash is '{}' ", new_hash);

    {
        auto ret = PatchIniHash(ini, new_hash);
        if (!ret) {
            XLOG::l("Failed to patch hash '{}' in INI '{}'", new_hash, ini);
            return false;
        }

        auto ini_hash = GetOldHashFromIni(ini);
        XLOG::d.t("Now hash in '{}'is '{}'", ini, ini_hash);
    }
    {
        auto ret = PatchStateHash(state, new_hash);
        if (!ret) {
            XLOG::l("Failed to patch hash '{}' in state '{}'", new_hash, state);
            return false;
        }

        auto state_hash = GetOldHashFromState(state);
        XLOG::d.t("Now hash in '{}'is '{}'", state, state_hash);
    }
    return true;
}

// this function is used to copy missing state files from the Legacy Agent to
// THIS IS MANUALLY TESTED FUNCTION. Refactor only after adding unit tests.
// Still, this function is temporary(to fix error in b3 beta) and may be removed
// at any moment
void RecoverOldStateFileWithPreemtiveHashPatch() {
    namespace fs = std::filesystem;
    XLOG::d.t(
        "Attempt to recover of the state file. This feature is temporary");

    fs::path path = FindLegacyAgent();
    if (path.empty()) {
        XLOG::d.i("Agent not found, quitting recover");
        return;
    }

    auto old_state = path / dirs::kAuStateLocation / files::kAuStateFile;
    std::error_code ec;
    if (!fs::is_regular_file(old_state, ec)) {
        XLOG::l.i("Error [{}] accessing'{}', no need to recover, quitting",
                  ec.value(), old_state);
        return;
    }

    fs::path new_path = cma::cfg::GetAuStateDir();
    auto new_state = new_path / files::kAuStateFile;
    if (fs::exists(new_path, ec) && fs::exists(new_state, ec)) {
        XLOG::l.i("'{}' and '{}' exist: no need to recover", new_path,
                  new_state);
        return;
    }

    // should not damage in any case
    PatchOldFilesWithDatHash();

    fs::create_directories(new_path, ec);
    fs::copy_file(old_state, new_state, ec);

    if (ec.value()) {
        XLOG::l.i("Error [{}] during copy from '{}' to '{}'", ec.value(),
                  old_state, new_state);
        return;
    }
    XLOG::l.i("Recovered '{}'", new_state);
}

// The only API entry DIRECTLY used in production
bool UpgradeLegacy(Force force_upgrade) {
    bool force = Force::yes == force_upgrade;

    if (force) {
        XLOG::d.i("Forced installation, Migration flag check is ignored");
    } else {
        if (!cma::install::IsMigrationRequired()) {
            XLOG::l.i("Migration is disabled in registry by installer");
            return false;
        }
    }

    XLOG::l.i("Starting upgrade(migration) process...");
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(
            "You have to be in elevated to use this function.\nPlease, run as Administrator");
        return false;
    }

    InfoOnStdio(force);

    auto protocol_dir = cma::cfg::GetUpgradeProtocolDir();
    {
        auto old_protocol_dir_1 = cma::cfg::GetRootDir();
        UpdateProtocolFile(protocol_dir, old_protocol_dir_1);

        auto old_protocol_dir_2 = cma::cfg::GetUserInstallDir();
        UpdateProtocolFile(protocol_dir, old_protocol_dir_2);
    }

    if (IsProtocolFileExists(protocol_dir) && !force) {
        XLOG::l.i(
            "Protocol File at '{}' exists, upgrade(migration) not required",
            wtools::ToUtf8(protocol_dir));
        RecoverOldStateFileWithPreemtiveHashPatch();
        return false;
    }

    auto path = FindLegacyAgent();
    if (path.empty()) {
        XLOG::l.t("Legacy Agent not found Upgrade is not possible");
        return true;
    }
    XLOG::l.i("Legacy Agent is found in '{}'", wtools::ToUtf8(path));

    PatchOldFilesWithDatHash();

    auto success = FindStopDeactivateLegacyAgent();
    if (!success) {
        XLOG::l("Legacy Agent is not possible to stop");
    }

    std::filesystem::path user_dir = cma::cfg::GetUserDir();

    // FOLDERS:
    auto count = CopyAllFolders(path, user_dir, CopyFolderMode::keep_old);
    count += CopyRootFolder(path, user_dir);

    // INI:
    XLOG::l.i("Converting ini file...");
    ConvertIniFiles(path, user_dir);

    // PROTOCOL:

    XLOG::l.i("Saving protocol file...");
    CreateProtocolFile(protocol_dir, {});

    return true;
}

std::optional<YAML::Node> LoadIni(std::filesystem::path File) {
    namespace fs = std::filesystem;
    std::error_code ec;

    if (!fs::exists(File, ec)) {
        XLOG::l.i("File not found '{}', this may be ok", File);
        return {};
    }
    if (!fs::is_regular_file(File, ec)) {
        XLOG::l.w("File '{}' is not a regular file, this is wrong", File);
        return {};
    }

    cma::cfg::cvt::Parser p;
    p.prepare();
    if (!p.readIni(File, false)) {
        XLOG::l.e("File '{}' is not a valid INI file, this is wrong", File);
        return {};
    }

    return p.emitYaml();
}

bool ConvertLocalIniFile(const std::filesystem::path &LegacyRoot,
                         const std::filesystem::path &ProgramData) {
    namespace fs = std::filesystem;
    const std::string local_ini = "check_mk_local.ini";
    auto local_ini_file = LegacyRoot / local_ini;
    std::error_code ec;
    if (fs::exists(local_ini_file, ec)) {
        XLOG::l.i("Converting local ini file '{}'", local_ini_file);
        auto user_yaml_file = wtools::ToUtf8(files::kDefaultMainConfigName);

        auto out_file =
            CreateUserYamlFromIni(local_ini_file, ProgramData, user_yaml_file);
        if (!out_file.empty() && fs::exists(out_file, ec)) {
            XLOG::l.i("Local File '{}' was converted as user YML file '{}'",
                      local_ini_file, out_file);
            return true;
        }
    }

    XLOG::l.t(
        "Local INI File was not converted, absent, has no data or other reason",
        local_ini_file);

    return false;
}

bool ConvertUserIniFile(
    const std::filesystem::path &legacy_root,
    const std::filesystem::path &pdata,  // programdata/checkmk/agent
    bool local_ini_exists) {
    namespace fs = std::filesystem;

    // simple sanity check
    if (cma::cfg::DetermineInstallationType() == InstallationType::wato) {
        XLOG::l("Bad Call for Bad Installation");
        return false;
    }

    auto user_ini_file = legacy_root / files::kIniFile;

    std::error_code ec;
    if (!fs::exists(user_ini_file, ec)) {
        XLOG::l.i("User ini File {} is absent", user_ini_file);
        return false;
    }

    XLOG::l.i("User ini File {} to be processed", user_ini_file);

    // check_mk.user.yml or check_mk.bakery.yml
    const auto name = wtools::ToUtf8(files::kDefaultMainConfigName);

    // generate
    auto out_folder = pdata;

    // if local.ini file exists, then second file must be a bakery file(pure
    // logic)
    auto ini_from_wato = IsBakeryIni(user_ini_file);
    fs::path yaml_file;

    if (ini_from_wato || local_ini_exists)
        yaml_file = CreateBakeryYamlFromIni(user_ini_file, out_folder, name);
    else
        yaml_file = CreateUserYamlFromIni(user_ini_file, out_folder, name);

    // check
    if (!yaml_file.empty() && fs::exists(yaml_file, ec)) {
        XLOG::l.t("User ini File {} was converted to YML file {}",
                  user_ini_file, yaml_file);
        return true;
    }

    XLOG::l.w("User ini File {} has no useful data", user_ini_file);
    return false;
}

// intermediate API, used indirectly
bool ConvertIniFiles(const std::filesystem::path &legacy_root,
                     const std::filesystem::path &program_data) {
    namespace fs = std::filesystem;
    using namespace cma::cfg;

    auto installation_type = cma::cfg::DetermineInstallationType();

    bool local_file_exists = ConvertLocalIniFile(legacy_root, program_data);

    // if installation is baked, than only local ini conversion allowed
    if (installation_type == InstallationType::wato) {
        auto ini_file = legacy_root / files::kIniFile;
        if (!cma::tools::IsValidRegularFile(ini_file)) {
            XLOG::d.i("File '{}' is absent, nothing to do",
                      ini_file.u8string());
            return local_file_exists;
        }

        XLOG::d(
            "You have Baked Agent installed.\nYour legacy configuration file '{}' exists and is {}\n"
            "The Upgrade of above mentioned file is SKIPPED to avoid overriding of your WATO managed configuration file '{}\\{}'\n\n"
            "If you do want to upgrade legacy configuration file, then you have to:\n"
            "\t- delete manually the file {}\\{}\n"
            "\t- call check_mk_agent.exe upgrade -force\n",
            ini_file.u8string(),

            IsBakeryIni(ini_file) ? "managed by Bakery/WATO" : "user defined",
            wtools::ToUtf8(cma::cfg::GetBakeryDir()),
            wtools::ToUtf8(files::kBakeryYmlFile),
            wtools::ToUtf8(files::kIniFile),
            wtools::ToUtf8(cma::cfg::GetRootInstallDir()),
            wtools::ToUtf8(files::kWatoIniFile)
            //
        );

        return local_file_exists;
    }

    auto user_or_bakery_exists =
        ConvertUserIniFile(legacy_root, program_data, local_file_exists);

    return local_file_exists || user_or_bakery_exists;
}

// read first line and check for a marker
bool IsBakeryIni(const std::filesystem::path &Path) noexcept {
    if (!cma::tools::IsValidRegularFile(Path)) return false;

    try {
        std::ifstream ifs(Path, std::ios::binary);
        if (!ifs) return false;

        char buffer[kBakeryMarker.size()];
        ifs.read(buffer, sizeof(buffer));
        if (!ifs) return false;
        return 0 == memcmp(buffer, kBakeryMarker.data(), sizeof(buffer));

    } catch (const std::exception &e) {
        XLOG::l(XLOG_FLINE + " Exception {}", e.what());
        return false;
    }
}

std::string MakeComments(const std::filesystem::path &source_file_path,
                         bool file_from_bakery) noexcept {
    return fmt::format(
        "# Converted to YML from the file '{}'\n"
        "{}\n",
        source_file_path.u8string(),
        file_from_bakery ? "# original INI file was managed by WATO\n"
                         : "# original INI file was managed by user\n");
}

bool StoreYaml(const std::filesystem::path &filename, YAML::Node yaml_node,
               const std::string &comment) noexcept {
    std::ofstream ofs(
        filename);  // text mode, required to have normal carriage return
    if (ofs) {
        ofs << comment;
        ofs << yaml_node;
    }

    return true;
}

std::filesystem::path CreateUserYamlFromIni(
    const std::filesystem::path &ini_file,      // ini file to use
    const std::filesystem::path &program_data,  // directory to send
    const std::string &yaml_name                // name to be used in output
    ) noexcept {
    namespace fs = std::filesystem;

    // conversion
    auto yaml = LoadIni(ini_file);
    if (!yaml.has_value() || !yaml.value().IsMap()) {
        XLOG::l.w("File '{}' is empty, no yaml created", ini_file);
        return {};
    }

    // storing
    auto comments = MakeComments(ini_file, false);
    auto yaml_file = program_data;

    std::error_code ec;
    if (!fs::exists(yaml_file, ec)) {
        fs::create_directories(yaml_file, ec);
    }

    yaml_file /= yaml_name;
    yaml_file.replace_extension(files::kDefaultUserExt);

    StoreYaml(yaml_file, yaml.value(), comments);
    XLOG::l.i("File '{}' is successfully converted", ini_file);

    return yaml_file;
}

std::filesystem::path CreateBakeryYamlFromIni(
    const std::filesystem::path &ini_file,      // ini file to use
    const std::filesystem::path &program_data,  // directory to send
    const std::string &yaml_name) noexcept {    // name to be used in output

    namespace fs = std::filesystem;

    // conversion
    auto yaml = LoadIni(ini_file);
    if (!yaml.has_value() || !yaml.value().IsMap()) {
        XLOG::l.w("File '{}' is empty, no yaml created", ini_file);
        return {};
    }

    // storing
    auto comments = MakeComments(ini_file, true);
    auto yaml_file = program_data;
    // check installation type
    auto agent_type = cma::cfg::DetermineInstallationType();

    if (agent_type == InstallationType::wato) {
        XLOG::l.w(
            "Legacy INI file is not converted,"
            " because This is Bakery Agent");
        return {};
    }

    yaml_file /= dirs::kBakery;

    std::error_code ec;
    if (!fs::exists(yaml_file, ec)) {
        fs::create_directories(yaml_file, ec);
    }

    yaml_file /= yaml_name;
    yaml_file.replace_extension(files::kDefaultBakeryExt);

    StoreYaml(yaml_file, yaml.value(), comments);
    XLOG::l.i("File '{}' is successfully converted", ini_file);

    return yaml_file;
}

std::filesystem::path FindOldIni() {
    std::filesystem::path path = FindLegacyAgent();
    if (path.empty()) {
        XLOG::d.t("Legacy Agent is not found");
        return {};
    }
    return path / files::kIniFile;
}

std::filesystem::path FindOldState() {
    std::filesystem::path path = FindLegacyAgent();
    if (path.empty()) {
        XLOG::d.t("Legacy Agent is not found");
        return {};
    }
    return path / dirs::kAuStateLocation / files::kAuStateFile;
}

std::string GetNewHash(const std::filesystem::path &dat) noexcept {
    try {
        auto yml = YAML::LoadFile(dat.u8string());
        auto hash = GetVal(yml, kHashName.data(), std::string());
        if (hash == cma::cfg::kBuildHashValue) {
            XLOG::l.t("Hash is from packaged agent, ignoring");
            return {};
        }

        return hash;

    } catch (const std::exception &e) {
        XLOG::l("can't load '{}', hash not known, exception '{}'",
                dat.u8string(), e.what());
        return {};
    }
}

std::string ReadHash(std::fstream &ifs) noexcept {
    try {
        char old_hash[17];
        ifs.read(old_hash, sizeof(old_hash) - 1);
        old_hash[sizeof(old_hash) - 1] = 0;
        if (strlen(old_hash) != 16) {
            XLOG::l("Bad hash in the ini");
            return {};
        }
        return old_hash;
    } catch (const std::exception &e) {
        XLOG::l("Exception'{}' when reading hash", e.what());
    }
    return {};
}

std::string GetOldHashFromFile(const std::filesystem::path &ini,
                               std::string_view marker) noexcept {
    try {
        std::fstream ifs;
        ifs.open(ini,
                 std::fstream::binary | std::fstream::in | std::fstream::out);

        std::string str((std::istreambuf_iterator<char>(ifs)),
                        std::istreambuf_iterator<char>());

        auto pos = str.find(marker);

        if (pos == std::string::npos) return {};

        ifs.seekp(pos + marker.size());

        return ReadHash(ifs);
    } catch (const std::exception &e) {
        XLOG::l("IO failed during reading hash from '{}', exception '{}' ",
                ini.u8string(), e.what());
        return {};
    }
}

std::string GetOldHashFromIni(const std::filesystem::path &ini) noexcept {
    return GetOldHashFromFile(ini, kIniHashMarker);
}

std::string GetOldHashFromState(const std::filesystem::path &state) noexcept {
    return GetOldHashFromFile(state, kStateHashMarker);
}

bool PatchHashInFile(const std::filesystem::path &ini, const std::string &hash,
                     std::string_view marker) noexcept {
    try {
        std::fstream ifs;
        ifs.open(ini,
                 std::fstream::binary | std::fstream::in | std::fstream::out);

        std::string str((std::istreambuf_iterator<char>(ifs)),
                        std::istreambuf_iterator<char>());

        auto pos = str.find(marker);

        if (pos == std::string::npos) return false;

        ifs.seekp(pos + marker.size());

        auto ret = ReadHash(ifs);
        if (ret.empty()) return false;

        ifs.seekp(pos + marker.size());
        ifs.write(hash.c_str(), 16);
        return true;
    } catch (const std::exception &e) {
        XLOG::l("IO failed during patching ini '{}' hash, exception '{}' ",
                e.what());
        return false;
    }
}

bool PatchIniHash(const std::filesystem::path &ini,
                  const std::string &hash) noexcept {
    return PatchHashInFile(ini, hash, kIniHashMarker);
}

bool PatchStateHash(const std::filesystem::path &ini,
                    const std::string &hash) noexcept {
    return PatchHashInFile(ini, hash, kStateHashMarker);
}

}  // namespace cma::cfg::upgrade

namespace cma::cfg::rm_lwa {

bool IsRequestedByRegistry() {
    using namespace cma::install;
    return std::wstring(registry::kMsiRemoveLegacyRequest) ==
           wtools::GetRegistryValue(registry::GetMsiRegistryPath(),
                                    registry::kMsiRemoveLegacy,
                                    registry::kMsiRemoveLegacyDefault);
}

void SetAlreadyRemoved() {
    using namespace cma::install;
    XLOG::l.i("Disabling in registry request to remove Legacy Agent");
    wtools::SetRegistryValue(registry::GetMsiRegistryPath(),
                             registry::kMsiRemoveLegacy,
                             registry::kMsiRemoveLegacyAlready);
}

bool IsAlreadyRemoved() {
    using namespace cma::install;
    return std::wstring(registry::kMsiRemoveLegacyAlready) ==
           wtools::GetRegistryValue(registry::GetMsiRegistryPath(),
                                    registry::kMsiRemoveLegacy,
                                    registry::kMsiRemoveLegacyDefault);
}

bool IsToRemove() {
    if (upgrade::FindLegacyAgent().empty()) {
        XLOG::t("No legacy agent - nothing to do");
        return false;
    }

    if (IsAlreadyRemoved()) {
        XLOG::l.i(
            "The Legacy Agent is already removed. "
            "To remove the Legacy Agent again, please, "
            "use command line or set registry entry HKLM\\{}\\{} to \"1\"",
            wtools::ToUtf8(cma::install::registry::GetMsiRegistryPath()),
            wtools::ToUtf8(cma::install::registry::kMsiRemoveLegacy));
        return false;
    }

    if (cma::cfg::GetVal(groups::kGlobal, vars::kGlobalRemoveLegacy, false)) {
        XLOG::l.i("Config requests to remove Legacy Agent");
        return true;
    }

    if (IsRequestedByRegistry()) {
        XLOG::l.i("Registry requests to remove Legacy Agent");
        return true;
    }

    return false;
}

void Execute() {
    if (!IsToRemove()) return;

    using namespace cma::cfg;

    // un-installation self
    auto x = std::thread([]() {
        XLOG::l.i("Requested remove of Legacy Agent...");
        auto result = UninstallProduct(products::kLegacyAgent);
        if (result) SetAlreadyRemoved();

        XLOG::l.i("Result of remove of Legacy Agent is [{}]", result);
    });

    if (x.joinable()) x.join();
}
}  // namespace cma::cfg::rm_lwa
