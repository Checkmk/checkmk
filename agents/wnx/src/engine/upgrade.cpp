// Windows Tools
#include <stdafx.h>

#include <cstdint>
#include <filesystem>
#include <string>

#include "yaml-cpp/yaml.h"

#include "tools/_misc.h"
#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "logger.h"

#include "cvt.h"

#include "upgrade.h"

namespace cma::cfg::upgrade {

// SERVICE_AUTO_START : SERVICE_DISABLED
enum class StartType {
    kDisable = SERVICE_DISABLED,
    kAutoStart = SERVICE_AUTO_START

};

int CopyAllFolders(const std::filesystem::path& LegacyRoot,
                   const std::filesystem::path& ProgramData) {
    namespace fs = std::filesystem;
    if (ProgramData.u8string().find("CheckMK\\Agent") == std::string::npos) {
        XLOG::l.crit("{} is bad folder", ProgramData.u8string());
        return 0;
    }

    const std::wstring folders[] = {L"config", L"plugins", L"local", L"mrpe",
                                    L"state"};
    auto count = 0;
    for_each(folders, std::end(folders),

             [LegacyRoot, ProgramData, &count](const std::wstring Folder) {
                 auto src = LegacyRoot / Folder;
                 auto tgt = ProgramData / Folder;
                 XLOG::l.t("Processing '{}':", src.u8string());  //
                 fs::remove_all(tgt);
                 fs::create_directories(tgt);
                 count++;
                 auto c = CopyFolderRecursive(src, tgt, [](fs::path P) {
                     XLOG::l.i("\tCopy '{}'", P.u8string(),
                               wtools::ConvertToUTF8(cma::cfg::GetTempDir()));
                     return true;
                 });
                 count += c;
             });
    return count;
}

// copies all files from root, exception is ini and exe
// returns count of files copied
int CopyRootFolder(const std::filesystem::path& LegacyRoot,
                   const std::filesystem::path& ProgramData) {
    namespace fs = std::filesystem;
    using namespace cma::tools;
    using namespace cma::cfg;

    auto count = 0;
    std::error_code ec;
    for (const auto& dirEntry : fs::directory_iterator(LegacyRoot, ec)) {
        const auto& p = dirEntry.path();
        if (fs::is_directory(p, ec)) continue;

        auto extension = p.extension();
        if (IsEqual(extension.wstring(), L".ini")) continue;
        if (IsEqual(extension.wstring(), L".exe")) continue;

        // Copy to the targetParentPath which we just created.
        fs::copy(p, ProgramData, fs::copy_options::overwrite_existing, ec);

        if (ec.value() == 0) {
            count++;
            continue;
        }

        XLOG::l("during copy from '{}' to '{}' error {}", p.u8string(),
                wtools::ConvertToUTF8(cma::cfg::GetUserDir()), ec.value());
    }

    return count;
}

// Recursively copies those files and folders from src to target which matches
// predicate, and overwrites existing files in target.
int CopyFolderRecursive(
    const std::filesystem::path& Source, const std::filesystem::path& Target,
    const std::function<bool(std::filesystem::path)>& Predicate) noexcept {
    namespace fs = std::filesystem;
    int count = 0;
    XLOG::l.t("Copy from '{}' to '{}'", Source.u8string(), Target.u8string());

    try {
        std::error_code ec;
        for (const auto& dirEntry :
             fs::recursive_directory_iterator(Source, ec)) {
            const auto& p = dirEntry.path();
            if (Predicate(p)) {
                // Create path in target, if not existing.
                const auto relativeSrc = fs::relative(p, Source);
                const auto targetParentPath = Target / relativeSrc;
                if (fs::is_directory(p))

                {
                    fs::create_directories(targetParentPath, ec);
                    if (ec.value() != 0) {
                        XLOG::l("Failed create folder '{} error {}",
                                targetParentPath.u8string(), ec.value());
                        continue;
                    }
                } else {
                    // Copy to the targetParentPath which we just created.
                    fs::copy(p, targetParentPath,
                             fs::copy_options::overwrite_existing, ec);
                    if (ec.value() == 0) {
                        count++;
                        continue;
                    }
                    XLOG::l("during copy from '{}' to '{}' error {}",
                            p.u8string(), targetParentPath.u8string(),
                            ec.value());
                }
            }
        }
    } catch (std::exception& e) {
        XLOG::l("Exception during copy file {}", e.what());
    }

    return count;
}

int GetServiceStatus(SC_HANDLE ServiceHandle) {
    DWORD bytes_needed = 0;
    SERVICE_STATUS_PROCESS ssp;

    if (!QueryServiceStatusEx(ServiceHandle, SC_STATUS_PROCESS_INFO,
                              (LPBYTE)&ssp, sizeof(SERVICE_STATUS_PROCESS),
                              &bytes_needed)) {
        XLOG::l("QueryServiceStatusEx failed {}", GetLastError());
        return -1;
    }
    return ssp.dwCurrentState;
}

uint32_t GetServiceHint(SC_HANDLE ServiceHandle) {
    DWORD bytes_needed = 0;
    SERVICE_STATUS_PROCESS ssp;

    if (!QueryServiceStatusEx(ServiceHandle, SC_STATUS_PROCESS_INFO,
                              (LPBYTE)&ssp, sizeof(SERVICE_STATUS_PROCESS),
                              &bytes_needed)) {
        XLOG::l("QueryServiceStatusEx failed {}", GetLastError());
        return 0;
    }
    return ssp.dwWaitHint;
}

int SendServiceCommand(SC_HANDLE Handle, uint32_t Command) {
    SERVICE_STATUS_PROCESS ssp;
    if (!ControlService(Handle, Command, (LPSERVICE_STATUS)&ssp)) {
        XLOG::l("ControlService failed {}", GetLastError());
        return -1;
    }
    return ssp.dwCurrentState;
}

std::pair<SC_HANDLE, SC_HANDLE> OpenServiceForControl(
    const std::wstring& Name) {
    auto manager_handle =
        OpenSCManager(nullptr,                 // local computer
                      nullptr,                 // ServicesActive database
                      SC_MANAGER_ALL_ACCESS);  // full access rights

    if (!manager_handle) {
        XLOG::l("OpenSCManager failed {}", GetLastError());
        return {nullptr, nullptr};
    }

    // Get a handle to the service.

    auto handle =
        OpenService(manager_handle,  // SCM database
                    Name.c_str(),    // name of service
                    SERVICE_STOP | SERVICE_START | SERVICE_QUERY_STATUS |
                        SERVICE_ENUMERATE_DEPENDENTS);

    if (!handle) {
        XLOG::l("OpenService {} failed {}", wtools::ConvertToUTF8(Name),
                GetLastError());
        return {manager_handle, handle};
    }
    return {manager_handle, handle};
}

int GetServiceStatusByName(const std::wstring& Name) {
    auto [manager_handle, handle] = OpenServiceForControl(Name);
    ON_OUT_OF_SCOPE(if (manager_handle) CloseServiceHandle(manager_handle));
    ON_OUT_OF_SCOPE(if (handle) CloseServiceHandle(handle));
    if (!handle) return -1;
    return GetServiceStatus(handle);
}

bool StopWindowsService(const std::wstring& Name) {
    XLOG::l.t("Service {} stopping ...", wtools::ConvertToUTF8(Name));
    // SERVICE_STATUS_PROCESS ssp;
    DWORD start_time = GetTickCount();
    DWORD timeout = 30000;  // 30-second time-out

    // Get a handle to the SCM database.
    auto [manager_handle, handle] = OpenServiceForControl(Name);
    ON_OUT_OF_SCOPE(if (manager_handle) CloseServiceHandle(manager_handle));
    ON_OUT_OF_SCOPE(if (handle) CloseServiceHandle(handle));
    if (!handle) return false;

    // Make sure the service is not already stopped.
    auto status = GetServiceStatus(handle);
    if (status == -1) return false;

    if (status == SERVICE_STOPPED) {
        XLOG::l.i("Service '{}' is already stopped.",
                  wtools::ConvertToUTF8(Name));
        return true;
    }

    auto hint = GetServiceHint(handle);
    // Do not wait longer than the wait hint. A good interval is
    // one-tenth of the wait hint but not less than 1 second
    // and not more than 10 seconds.
    auto delay = hint / 10;
    if (delay < 1000)
        delay = 1000;
    else if (delay > 10000)
        delay = 10000;

    // If a stop is pending, wait for it.
    if (status == SERVICE_STOP_PENDING) XLOG::l.t("Service stop pending...");

    while (status == SERVICE_STOP_PENDING) {
        cma::tools::sleep(delay);

        status = GetServiceStatus(handle);
        if (status == -1) return false;

        if (status == SERVICE_STOPPED) {
            XLOG::l.i("Service stopped successfully.");
            return true;
        }

        if (GetTickCount() - start_time > timeout) {
            XLOG::l("Service stop timed out during pending");
            return false;
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
        if (status == SERVICE_STOPPED) return true;

        if (GetTickCount() - start_time > timeout) {
            XLOG::l("Wait timed out for '{}'", wtools::ConvertToUTF8(Name));
            return false;
        }
    }

    XLOG::l.i("Service stopped successfully");
    return true;
}

bool StartWindowsService(const std::wstring& Name) {
    // SERVICE_STATUS_PROCESS ssp;
    DWORD start_time = GetTickCount();
    DWORD timeout = 30000;  // 30-second time-out

    // Get a handle to the SCM database.
    auto [manager_handle, handle] = OpenServiceForControl(Name);
    ON_OUT_OF_SCOPE(if (manager_handle) CloseServiceHandle(manager_handle));
    ON_OUT_OF_SCOPE(if (handle) CloseServiceHandle(handle));
    if (!handle) return false;

    // Make sure the service is not already stopped.
    auto status = GetServiceStatus(handle);
    switch (status) {
        case -1:
            return false;
        case SERVICE_RUNNING:
            XLOG::l.i("Service is already running.");
            return true;
        case SERVICE_STOPPED:
            break;
        case SERVICE_STOP_PENDING:
        default:
            XLOG::l.i(
                "Service is in strange and stupid mode = {}. This is not a problem, just Windows Feature",
                status);
            wtools::KillProcess(Name + L".exe", 1);
            break;
    }

    // Send a start code to the service.
    auto ret = ::StartService(handle, 0, nullptr);
    if (ret)
        XLOG::l.i("Service '{}' started successfully ",
                  wtools::ConvertToUTF8(Name));
    else {
        auto err = GetLastError();
        if (err == 1056) {
            XLOG::l.t("Service '{}' already started",
                      wtools::ConvertToUTF8(Name));
            return true;
        }
        XLOG::l("Service '{}' start failed {} ", wtools::ConvertToUTF8(Name),
                err);
    }

    return true;
}

bool WinServiceChangeStartType(const std::wstring Name, StartType Type) {
    auto manager_handle = OpenSCManager(nullptr, nullptr, SC_MANAGER_CONNECT);
    if (!manager_handle) {
        XLOG::l.crit("Cannot open SC MAnager {}", GetLastError());
        return false;
    }
    ON_OUT_OF_SCOPE(CloseServiceHandle(manager_handle));

    auto handle =
        OpenService(manager_handle, Name.c_str(), SERVICE_CHANGE_CONFIG);
    if (!handle) {
        XLOG::l.crit("Cannot open Service {}, error =  {}",
                     wtools::ConvertToUTF8(Name), GetLastError());
        return false;
    }
    ON_OUT_OF_SCOPE(CloseServiceHandle(handle));

    auto result =
        ChangeServiceConfig(handle,             // handle of service
                            SERVICE_NO_CHANGE,  // service type: no change
                            static_cast<DWORD>(Type),  // service start type
                            SERVICE_NO_CHANGE,  // error control: no change
                            nullptr,            // binary path: no change
                            nullptr,            // load order group: no change
                            nullptr,            // tag ID: no change
                            nullptr,            // dependencies: no change
                            nullptr,            // account name: no change
                            nullptr,            // password: no change
                            nullptr);           // display name: no change
    if (!result) {
        XLOG::l("ChangeServiceConfig {} failed {}", wtools::ConvertToUTF8(Name),
                GetLastError());
        return false;
    }

    return true;
}

std::wstring FindLegacyAgent() {
    namespace fs = std::filesystem;
    auto image_path = wtools::GetRegistryValue(
        L"SYSTEM\\CurrentControlSet\\Services\\check_mk_agent", L"ImagePath",
        L"");

    if (image_path.empty()) return {};

    if (image_path.back() == L'\"') image_path.pop_back();
    auto path = image_path.c_str();
    if (*path == L'\"') ++path;

    fs::path p = path;
    std::error_code ec;
    if (!fs::exists(p, ec) || !fs::is_regular_file(p, ec)) {
        XLOG::d(
            "Agent is found in registry {}, but absent on the disk. Assuming that now agenny installed",
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
    return WinServiceChangeStartType(L"check_mk_agent", StartType::kAutoStart);
}
bool DeactivateLegacyAgent() {
    wtools::SetRegistryValue(
        L"SYSTEM\\CurrentControlSet\\Services\\check_mk_agent", L"StartType",
        SERVICE_DISABLED);
    /*
        wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);
        RegDeleteKey(HKEY_LOCAL_MACHINE,
                     L"SYSTEM\\CurrentControlSet\\Services\\WinRing0_1_2_0");
    */
    return WinServiceChangeStartType(L"check_mk_agent", StartType::kDisable);
}

int WaitForStatus(std::function<int(const std::wstring&)> StatusChecker,
                  const std::wstring& ServiceName, int ExpectedStatus,
                  int Time) {
    int status = -1;
    while (1) {
        status = StatusChecker(ServiceName);
        if (status == ExpectedStatus) return status;
        if (Time >= 0) {
            Sleep(1000);
            XLOG::l.i("1 second is over status is {}, t=required {}...", status,
                      ExpectedStatus);
        } else
            break;
        Time -= 1000;
    }

    return status;
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
        if (!wtools::KillProcess(L"check_mk_agent.exe", 9)) return false;
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
    wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);

    XLOG::l.t("Stopping winring0_1_2_0...");
    StopWindowsService(L"winring0_1_2_0");
    status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                           SERVICE_STOPPED, 5000);
    if (status != SERVICE_STOPPED) {
        auto driver_body = details::FindServiceImagePath(L"winring0_1_2_0");
        if (driver_body.empty()) {
            if (status == SERVICE_STOP_PENDING) {
                XLOG::l.crit(
                    "Can't stop windows kernel driver 'winring0_1_2_0', integral part of Open Hardware Monitor\n"
                    "'winring0_1_2_0' registry entry is absent, but driver is running having 'SERVICE_STOP_PENDING' state\n"
                    "THIS IS ABNORMAL. You must REBOOT Windows. And repeat action.");
            } else {
                xlog::sendStringToStdio("This is not error, just info: ",
                                        xlog::internal::Colors::kGreen);
                XLOG::l.w(
                    "Can't stop winring0_1_2_0, probably you have no 'Open Hardware Monitor' running.");
            }
        } else {
            xlog::sendStringToStdio("Probably you have : ",
                                    xlog::internal::Colors::kGreen);
            XLOG::l.crit("Failed to stop kernel legacy driver winring0_1_2_0");
        }
        return false;
    }

    return true;
}

bool FindActivateStartLegacyAgent(bool StartOhm) {
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

    if (StartOhm) {
        fs::path ohm = path;
        ohm /= "bin";
        ohm /= "OpenHardwareMonitorCLI.exe";
        std::error_code ec;
        if (!fs::exists(ohm, ec))
            XLOG::l.crit(
                "OpenHardwareMonitor not installed, please, add it to the Legacy Agent folder");
        else {
            XLOG::l.t("Starting open hardware monitor...");
            RunDetachedProcess(ohm.wstring());
            WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                          SERVICE_RUNNING, 5000);
        }
    }

    return true;
}

bool RunDetachedProcess(const std::wstring& Name) {
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
        NULL,          // Process handle not inheritable
        NULL,          // Thread handle not inheritable
        FALSE,         // Set handle inheritance to FALSE
        CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,  // No creation flags
        NULL,  // Use parent's environment block
        NULL,  // Use parent's starting directory
        &si,   // Pointer to STARTUPINFO structure
        &pi);  // Pointer to PROCESS_INFORMATION structure
    if (ret != TRUE) {
        XLOG::l("Cant start the process {}, error is {}",
                wtools::ConvertToUTF8(Name), GetLastError());
    }
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    return ret == TRUE;
}

std::string GetTimeString() {
    using namespace std::chrono;
    auto cur_time = system_clock::now();
    auto in_time_t = system_clock::to_time_t(cur_time);
    std::stringstream sss;
    auto ms = duration_cast<milliseconds>(cur_time.time_since_epoch()) % 1000;
    auto loc_time = std::localtime(&in_time_t);
    auto p_time = std::put_time(loc_time, "%Y-%m-%d %T");
    sss << p_time << "." << std::setfill('0') << std::setw(3) << ms.count()
        << std::ends;

    return sss.str().c_str();
}

bool CreateProtocolFile(std::filesystem::path ProtocolFile,
                        const std::string_view OptionalContent) {
    try {
        std::ofstream ofs(ProtocolFile, std::ios::binary);

        if (ofs) {
            ofs << "Upgraded:\n";
            ofs << "  time: '" << GetTimeString() << "'\n";
            if (OptionalContent.size()) {
                ofs << OptionalContent;
                ofs << "\n";
            }
        }
    } catch (const std::exception& e) {
        XLOG::l.crit("Exception during creatin protocol file {}", e.what());
        return false;
    }
    return true;
}

// The only API entry DIRECTLY used in production
bool UpgradeLegacy(bool ForceUpdate) {
    XLOG::l.i("Starting upgrade process...");
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(
            "You have to be in elevated to use this function.\nPlease, run as Administrator");
        return false;
    }
    if (ForceUpdate) {
        xlog::sendStringToStdio("Update is forced by command line\n",
                                xlog::internal::kYellow);
    }
    namespace fs = std::filesystem;
    fs::path protocol_file = cma::cfg::GetRootDir();
    protocol_file /= cma::cfg::files::kUpgradeProtocol;
    std::error_code ec;

    if (fs::exists(protocol_file, ec) && !ForceUpdate) {
        XLOG::l.i("Protocol File {} exists, upgrade not required",
                  protocol_file.u8string());
        return false;
    }

    auto path = FindLegacyAgent();
    if (path.empty()) {
        XLOG::l.t("Legacy Agent not found Upgrade is not possible");
        return true;
    } else {
        XLOG::l.i("Legacy Agent is found in '{}'", wtools::ConvertToUTF8(path));
    }
    auto success = FindStopDeactivateLegacyAgent();
    if (!success) {
        XLOG::l("Legacy Agent is not possible to stop");
    }

    auto count = CopyAllFolders(path, cma::cfg::GetUserDir());

    count += CopyRootFolder(path, cma::cfg::GetUserDir());

    ConvertIniFiles(path, cma::cfg::GetUserDir());

    // making protocol file:
    CreateProtocolFile(protocol_file, {});

    return true;
}

std::optional<YAML::Node> LoadIni(std::filesystem::path File) {
    namespace fs = std::filesystem;
    std::error_code ec;

    if (!fs::exists(File, ec)) {
        XLOG::l.i("File not found '{}', this is may be ok", File.u8string());
        return {};
    }
    if (!fs::is_regular_file(File, ec)) {
        XLOG::l.w("File '{}' is not a regular file, this is wrong",
                  File.u8string());
        return {};
    }

    cma::cfg::cvt::Parser p;
    p.prepare();
    if (!p.readIni(File, false)) {
        XLOG::l.e("File '{}' is not a valid INI file, this is wrong",
                  File.u8string());
        return {};
    }

    return p.emitYaml();
}

bool ConvertLocalIniFile(const std::filesystem::path& LegacyRoot,
                         const std::filesystem::path& ProgramData) {
    namespace fs = std::filesystem;
    const std::string local_ini = "check_mk_local.ini";
    auto local_ini_file = LegacyRoot / local_ini;
    std::error_code ec;
    if (fs::exists(local_ini_file, ec)) {
        XLOG::l.t("Converting local ini file {}", local_ini_file.u8string());
        auto user_yaml_file =
            wtools::ConvertToUTF8(std::wstring(files::kDefaultMainConfigName));
        auto out_file =
            CreateYamlFromIniSmart(local_ini_file, ProgramData, user_yaml_file);
        if (!out_file.empty() && fs::exists(out_file, ec)) {
            XLOG::l.t("Local File {} was converted as user YML file {}",
                      local_ini_file.u8string(), out_file.u8string());
            return true;
        }
    }

    XLOG::l.t("Local ini File is absent or has no data",
              local_ini_file.u8string());
    return false;
}

bool ConvertUserIniFile(const std::filesystem::path& LegacyRoot,
                        const std::filesystem::path& ProgramData,
                        bool LocalFileExists) {
    namespace fs = std::filesystem;

    const std::string root_ini = "check_mk.ini";
    auto user_ini_file = LegacyRoot / root_ini;

    std::error_code ec;
    if (!fs::exists(user_ini_file, ec)) {
        XLOG::l.i("User ini File {} is absent", user_ini_file.u8string());
        return false;
    }

    // check_mk.user.yml or check_mk.bakery.yml
    const std::wstring name = files::kDefaultMainConfigName;

    // generate
    auto out_folder = ProgramData;
    auto yaml_file =
        CreateYamlFromIniSmart(user_ini_file, out_folder,
                               wtools::ConvertToUTF8(name), LocalFileExists);
    // check
    if (!yaml_file.empty() && fs::exists(yaml_file, ec)) {
        XLOG::l.t("User ini File {} was converted to YML file {}",
                  user_ini_file.u8string(), yaml_file.u8string());
        return true;
    }

    XLOG::l.w("User ini File {} has no useful data", user_ini_file.u8string());
    return false;
}

// intermediate API, used indirectly
bool ConvertIniFiles(const std::filesystem::path& LegacyRoot,
                     const std::filesystem::path& ProgramData) {
    namespace fs = std::filesystem;
    using namespace cma::cfg;
    {
        std::error_code ec;
        auto user_ini = (ProgramData / files::kDefaultMainConfig)
                            .replace_extension(files::kDefaultUserExt);
        XLOG::l.t("Removing {}", user_ini.u8string());
        fs::remove(user_ini, ec);
    }

    {
        std::error_code ec;
        auto bakery_ini =
            (ProgramData / dirs::kBakery / files::kDefaultMainConfig)
                .replace_extension(files::kDefaultBakeryExt);
        XLOG::l.t("Removing {}", bakery_ini.u8string());
        fs::remove(bakery_ini, ec);
    }
    bool local_file_exists = ConvertLocalIniFile(LegacyRoot, ProgramData);

    auto user_or_bakery_exists =
        ConvertUserIniFile(LegacyRoot, ProgramData, local_file_exists);

    return local_file_exists || user_or_bakery_exists;
}

// read first line and check for a marker
bool IsBakeryIni(const std::filesystem::path Path) noexcept {
    namespace fs = std::filesystem;
    std::error_code ec;
    if (!fs::exists(Path, ec)) return false;

    if (!fs::is_regular_file(Path, ec)) return false;

    try {
        std::ifstream ifs(Path, std::ios::binary);
        if (!ifs) return false;

        char buffer[kBakeryMarker.size()];
        ifs.read(buffer, sizeof(buffer));
        if (!ifs) return false;
        return 0 == memcmp(buffer, kBakeryMarker.data(), sizeof(buffer));

    } catch (const std::exception& e) {
        XLOG::l(XLOG_FLINE + " Exception {}", e.what());
        return false;
    }
}

std::string MakeComments(const std::filesystem::path SourceFilePath,
                         bool Bakery) noexcept {
    return fmt::format(
        "# Converted from '{}'\n"
        "{}\n",
        SourceFilePath.u8string(),
        Bakery ? "# original INI file was managed by WATO(from bakery)\n"
               : "# original INI file was managed by user\n");
}

bool StoreYaml(const std::filesystem::path File, const YAML::Node Yaml,
               const std::string Comment) noexcept {
    std::ofstream ofs(File, std::ios::binary);
    if (ofs) {
        ofs << Comment;
        ofs << Yaml;
    }

    return true;
}

std::filesystem::path CreateYamlFromIniSmart(
    const std::filesystem::path IniFile,  // ini file to use
    const std::filesystem::path Pd,       // directory to send
    const std::string YamlName,           // name to be used in output
    bool ForceBakeryFile) noexcept {      // in some create bakery!
    namespace fs = std::filesystem;
    auto yaml = LoadIni(IniFile);

    if (!yaml.has_value() || !yaml.value().IsMap()) {
        XLOG::l.w("File {} is empty, no yaml created", IniFile.u8string());
        return {};
    }

    std::filesystem::path yaml_file;
    auto bakery_file = ForceBakeryFile || IsBakeryIni(IniFile);
    auto comments = MakeComments(IniFile, bakery_file);
    yaml_file = Pd;
    if (bakery_file) yaml_file /= dirs::kBakery;
    std::error_code ec;
    if (!fs::exists(yaml_file, ec)) {
        fs::create_directories(yaml_file, ec);
    }
    yaml_file /= YamlName;
    yaml_file.replace_extension(bakery_file ? files::kDefaultBakeryExt
                                            : files::kDefaultUserExt);

    StoreYaml(yaml_file, yaml.value(), comments);
    XLOG::l.i("File {} is successfully converted", IniFile.u8string());
    return yaml_file;
}

}  // namespace cma::cfg::upgrade
