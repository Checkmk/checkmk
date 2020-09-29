// Windows Tools
#include "stdafx.h"

#include "wtools.h"

// WINDOWS STUFF
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <WinSock2.h>

#include <comdef.h>
#include <shellapi.h>

#include "psapi.h"
#pragma comment(lib, "wbemuuid.lib")  /// Microsoft Specific
#pragma comment(lib, "psapi.lib")     /// Microsoft Specific
#pragma comment(lib, "Sensapi.lib")   /// Microsoft Specific
#endif

#include <cstdint>
#include <numeric>
#include <random>
#include <string>

#include "cap.h"
#include "cfg.h"
#include "common/wtools_runas.h"
#include "common/wtools_user_control.h"
#include "logger.h"
#include "tools/_raii.h"
#include "upgrade.h"

namespace wtools {
std::pair<uint32_t, uint32_t> GetProcessExitCode(uint32_t pid) {
    auto h = ::OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,  // not on XP
                           FALSE, pid);
    if (nullptr == h) return {0, GetLastError()};

    ON_OUT_OF_SCOPE(::CloseHandle(h));
    DWORD exit_code = 0;
    auto success = ::GetExitCodeProcess(h, &exit_code);
    if (FALSE == success) return {-1, GetLastError()};

    return {exit_code, 0};
}

std::wstring GetProcessPath(uint32_t pid) noexcept {
    auto h =
        ::OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (h == nullptr) return {};
    ON_OUT_OF_SCOPE(::CloseHandle(h));

    wchar_t buffer[MAX_PATH];
    if (::GetModuleFileNameEx(h, 0, buffer, MAX_PATH)) return buffer;

    return {};
}

// returns count of killed processes
int KillProcessesByDir(const std::filesystem::path& dir) noexcept {
    namespace fs = std::filesystem;
    constexpr size_t kMinimumPathLen = 16;  // safety

    if (dir.empty()) return -1;

    if (dir.u8string().size() < kMinimumPathLen) return -1;

    int killed_count = 0;

    ScanProcessList([dir, &killed_count,
                     kMinimumPathLen](const PROCESSENTRY32W& entry) -> bool {
        auto pid = entry.th32ProcessID;
        auto exe = wtools::GetProcessPath(pid);
        if (exe.length() < kMinimumPathLen) return true;  // skip short path

        fs::path p{exe};

        auto shift = p.lexically_relative(dir).u8string();
        if (!shift.empty() && shift[0] != '.') {
            KillProcess(pid);
            killed_count++;
        }
        return true;  // continue, we want to scan all process in the system
    });

    return killed_count;
}

void AppRunner::prepareResources(std::wstring_view command_line,
                                 bool create_pipe) noexcept {
    if (create_pipe) {
        stdio_.create();
        stderr_.create();
    }

    cmd_line_ = command_line;
    job_handle_ = nullptr;
    process_handle_ = nullptr;
}

void AppRunner::cleanResources() noexcept {
    job_handle_ = nullptr;
    process_handle_ = nullptr;
    stdio_.shutdown();
    stderr_.shutdown();
}

// returns PID or 0,
uint32_t AppRunner::goExecAsJob(std::wstring_view CommandLine) noexcept {
    try {
        if (process_id_) {
            XLOG::l.bp("Attempt to reuse AppRunner");
            return 0;
        }

        prepareResources(CommandLine, true);

        auto [pid, jh, ph] = cma::tools::RunStdCommandAsJob(
            CommandLine.data(), true, stdio_.getWrite(), stderr_.getWrite());
        // store data to reuse
        process_id_ = pid;
        job_handle_ = jh;
        process_handle_ = ph;

        // check and return on success
        if (process_id_) return process_id_;

        // failure s here
        XLOG::l(XLOG_FLINE + " Failed RunStd: [{}]*", GetLastError());

        cleanResources();

        return 0;
    } catch (const std::exception& e) {
        XLOG::l.crit(XLOG_FLINE + " unexpected exception: '{}'", e.what());
    }
    return 0;
}

uint32_t AppRunner::goExecAsJobAndUser(std::wstring_view user,
                                       std::wstring_view password,
                                       std::wstring_view CommandLine) noexcept {
    try {
        if (process_id_) {
            XLOG::l.bp("Attempt to reuse AppRunner");
            return 0;
        }

        prepareResources(CommandLine, true);

        auto [pid, jh, ph] =
            runas::RunAsJob(user, password, CommandLine.data(), true,
                            stdio_.getWrite(), stderr_.getWrite());
        // store data to reuse
        process_id_ = pid;
        job_handle_ = jh;
        process_handle_ = ph;

        // check and return on success
        if (process_id_) return process_id_;

        // failure s here
        XLOG::l(XLOG_FLINE + " Failed RunStd: [{}]*", GetLastError());

        cleanResources();

        return 0;
    } catch (const std::exception& e) {
        XLOG::l.crit(XLOG_FLINE + " unexpected exception: '{}'", e.what());
    }
    return 0;
}

// returns process id
uint32_t AppRunner::goExecAsUpdater(std::wstring_view CommandLine) noexcept {
    try {
        if (process_id_) {
            XLOG::l.bp("Attempt to reuse AppRunner/updater");
            return 0;
        }
        prepareResources(CommandLine, true);

        process_id_ = cma::tools::RunStdCommand(
            CommandLine, false, true, stdio_.getWrite(), stderr_.getWrite(),
            CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS);

        // check and return on success
        if (process_id_) return process_id_;

        // failure s here
        XLOG::l(XLOG_FLINE + " Failed updater RunStd: [{}]*", GetLastError());

        cleanResources();
        return 0;

    } catch (const std::exception& e) {
        XLOG::l.crit(XLOG_FLINE + " unexpected exception: '{}'", e.what());
    }
    return 0;
}

std::mutex ServiceController::s_lock_;
ServiceController* ServiceController::s_controller_ = nullptr;

// normal API
ServiceController::ServiceController(
    std::unique_ptr<wtools::BaseServiceProcessor> Processor) {
    if (nullptr == Processor) {
        XLOG::l.crit("Processor is nullptr unique");
        return;
    }
    std::lock_guard lk(s_lock_);
    if (processor_ == nullptr && s_controller_ == nullptr) {
        processor_ = std::move(Processor);
        s_controller_ = this;
    }
}

void WINAPI ServiceController::ServiceMain(DWORD Argc, wchar_t** Argv) {
    // Register the handler function for the service
    XLOG::l.i("Service Main");
    s_controller_->Start(Argc, Argv);
}

// no return from here
// can print on screen
ServiceController::StopType ServiceController::registerAndRun(
    const wchar_t* ServiceName,  //
    bool CanStop,                // t
    bool CanShutdown,            // t
    bool CanPauseContinue) {     // t
    if (!processor_) {
        XLOG::l.bp("No processor");
        return StopType::fail;
    }
    if (!ServiceName) {
        XLOG::l.bp("No Service name");
        return StopType::fail;
    }

    // strange code below
    auto allocated = new wchar_t[wcslen(ServiceName) + 1];
#pragma warning(push)
#pragma warning(disable : 4996)  //_CRT_SECURE_NO_WARNINGS
    wcscpy(allocated, ServiceName);
#pragma warning(pop)
    name_.reset(allocated);

    initStatus(CanStop, CanShutdown, CanPauseContinue);

    SERVICE_TABLE_ENTRY serviceTable[] = {{allocated, ServiceMain},
                                          {NULL, NULL}};

    // Connects the main thread of a service process to the service
    // control manager, which causes the thread to be the service
    // control dispatcher thread for the calling process. This call
    // returns when the service has stopped. The process should simply
    // terminate when the call returns. Two words: Blocks Here
    try {
        auto ret = ::StartServiceCtrlDispatcher(serviceTable);
        if (!ret) {
            auto error = GetLastError();

            // this normal situation when we are starting service from
            // command line without parameters
            if (error == ERROR_FAILED_SERVICE_CONTROLLER_CONNECT)
                return StopType::no_connect;

            XLOG::l(XLOG::kStdio)
                .crit("Cannot Start Service '{}' error = [{}]",
                      ConvertToUTF8(ServiceName), error);
            return StopType::fail;
        }
        return StopType::normal;
    } catch (std::exception& e) {
        XLOG::l(XLOG::kStdio)
            .crit("Exception '{}' in Service start with error [{}]", e.what(),
                  GetLastError());
    } catch (...) {
        XLOG::l(XLOG::kStdio)
            .crit("Exception in Service start with error [{}]", GetLastError());
    }
    return StopType::fail;
}

//
//   FUNCTION: InstallService
//
//   PURPOSE: Install the current application as a service to the local
//   service control manager database.
//
//   PARAMETERS:
//   * ServiceName - the name of the service to be installed
//   * DisplayName - the display name of the service
//   * dwStartType - the service start option. This parameter can be one of
//     the following values: SERVICE_AUTO_START, SERVICE_BOOT_START,
//     SERVICE_DEMAND_START, SERVICE_DISABLED, SERVICE_SYSTEM_START.
//   * Dependencies - a pointer to a double null-terminated array of null-
//     separated names of services or load ordering groups that the system
//     must start before this service.
//   * Account - the name of the account under which the service runs.
//   * Password - the password to the account name.
//
//   NOTE: If the function fails to install the service, it prints the error
//   in the standard output stream for users to diagnose the problem.
//
bool InstallService(const wchar_t* ServiceName, const wchar_t* DisplayName,
                    uint32_t StartType, const wchar_t* Dependencies,
                    const wchar_t* Account, const wchar_t* Password) {
    wchar_t service_path[MAX_PATH];
    XLOG::setup::ColoredOutputOnStdio(true);

    auto ret = ::GetModuleFileName(NULL, service_path, ARRAYSIZE(service_path));
    if (ret == 0) {
        XLOG::l(XLOG::kStdio)
            .crit("GetModuleFileName failed w/err {:#X}", GetLastError());
        return false;
    }

    // Open the local default service control manager database
    auto service_manager = ::OpenSCManager(
        NULL, NULL, SC_MANAGER_CONNECT | SC_MANAGER_CREATE_SERVICE);

    if (!service_manager) {
        XLOG::l(XLOG::kStdio)
            .crit("OpenSCManager failed w/err {:#X}", GetLastError());
        return false;
    }

    ON_OUT_OF_SCOPE(CloseServiceHandle(service_manager););

    // Install the service into SCM by calling CreateService
    auto service = ::CreateService(service_manager,       // SCManager database
                                   ServiceName,           // Name of service
                                   DisplayName,           // Name to display
                                   SERVICE_QUERY_STATUS,  // Desired access
                                   SERVICE_WIN32_OWN_PROCESS,  // Service type
                                   StartType,             // Service start type
                                   SERVICE_ERROR_NORMAL,  // Error control type
                                   service_path,          // Service's binary
                                   NULL,          // No load ordering group
                                   NULL,          // No tag identifier
                                   Dependencies,  // Dependencies
                                   Account,       // Service running account
                                   Password       // Password of the account
    );
    if (!service) {
        auto error = GetLastError();
        if (error == ERROR_SERVICE_EXISTS) {
            XLOG::l(XLOG::kStdio)
                .crit("The Service '{}' already exists",
                      wtools::ConvertToUTF8(ServiceName));
            return false;
        }
        XLOG::l(XLOG::kStdio).crit("CreateService failed w/err {}", error);
    }
    ON_OUT_OF_SCOPE(CloseServiceHandle(service););

    XLOG::l(XLOG::kStdio)
        .i("The Service '{}' is installed.", ConvertToUTF8(ServiceName));

    return true;
}

//
//   FUNCTION: UninstallService
//
//   PURPOSE: Stop and remove the service from the local service control
//   manager database.
//
//   PARAMETERS:
//   * ServiceName - the name of the service to be removed.
//
//   NOTE: If the function fails to uninstall the service, it prints the
//   error in the standard output stream for users to diagnose the problem.
//
// StopService by default is true, use false only during testing
bool UninstallService(const wchar_t* service_name,
                      UninstallServiceMode uninstall_mode) {
    XLOG::setup::ColoredOutputOnStdio(true);
    if (service_name == nullptr) {
        XLOG::l(XLOG::kStdio).crit("Parameter is null");
        return false;
    }
    auto name = wtools::ConvertToUTF8(service_name);
    // Open the local default service control manager database
    auto service_manager = ::OpenSCManager(NULL, NULL, SC_MANAGER_CONNECT);
    if (!service_manager) {
        XLOG::l(XLOG::kStdio)
            .crit("OpenSCManager failed, [{}]", GetLastError());
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(service_manager););

    // Open the service with delete, stop, and query status permissions
    auto service = ::OpenService(service_manager, service_name,
                                 SERVICE_STOP | SERVICE_QUERY_STATUS | DELETE);
    if (!service) {
        auto error = GetLastError();
        if (error == ERROR_SERVICE_DOES_NOT_EXIST) {
            XLOG::l(XLOG::kStdio).crit("The Service '{}' doesn't exist", name);
            return false;
        }

        XLOG::l(XLOG::kStdio).crit("OpenService '{}' failed, [{}]", name);
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(service););

    if (uninstall_mode == UninstallServiceMode::normal) {
        // Try to stop the service
        SERVICE_STATUS ssSvcStatus = {};
        if (::ControlService(service, SERVICE_CONTROL_STOP, &ssSvcStatus)) {
            XLOG::l(XLOG::kStdio).i("Stopping '{}'.", name);
            Sleep(1000);

            while (::QueryServiceStatus(service, &ssSvcStatus)) {
                if (ssSvcStatus.dwCurrentState == SERVICE_STOP_PENDING) {
                    xlog::sendStringToStdio(".");
                    Sleep(1000);
                } else
                    break;
            }

            if (ssSvcStatus.dwCurrentState == SERVICE_STOPPED) {
                XLOG::l(XLOG::kStdio).i("\n{} is stopped.", name);
            } else {
                XLOG::l(XLOG::kStdio).i("\n{} failed to stop.", name);
            }
        }
    }

    // Now remove the service by calling DeleteService.
    if (!::DeleteService(service)) {
        XLOG::l(XLOG::kStdio)
            .i("DeleteService for '{}' failed [{}]\n", name, GetLastError());
        return false;
    }

    XLOG::l(XLOG::kStdio)
        .i("The Service '{}' is successfully removed.\n", name);
    return true;
}

void ServiceController::initStatus(bool CanStop, bool CanShutdown,
                                   bool CanPauseContinue) {
    // The service runs in its own process.
    status_.dwServiceType = SERVICE_WIN32_OWN_PROCESS;

    // The service is starting.
    status_.dwCurrentState = SERVICE_START_PENDING;

    // The accepted commands of the service.
    DWORD controls_accepted = 0;
    if (CanStop) controls_accepted |= SERVICE_ACCEPT_STOP;
    if (CanShutdown) controls_accepted |= SERVICE_ACCEPT_SHUTDOWN;
    if (CanPauseContinue) controls_accepted |= SERVICE_ACCEPT_PAUSE_CONTINUE;
    status_.dwControlsAccepted = controls_accepted;

    status_.dwWin32ExitCode = NO_ERROR;
    status_.dwServiceSpecificExitCode = 0;
    status_.dwCheckPoint = 0;
    status_.dwWaitHint = 0;
}
//
//   FUNCTION: ServiceController::Stop()
//
//   PURPOSE: The function stops the service. It calls the OnStop
//   virtual function in which you can specify the actions to take when
//   the service stops. If an error occurs, the error will be logged in
//   the Application event log, and the service will be restored to the
//   original state.
//
void ServiceController::Stop() {
    if (!processor_) return;  // #TODO: trace

    auto original_state = status_.dwCurrentState;
    auto log_name = processor_->getMainLogName();
    try {
        // Tell SCM that the service is stopping.
        setServiceStatus(SERVICE_STOP_PENDING);

        // Perform service-specific stop operations.
        processor_->stopService();

        // Tell SCM that the service is stopped.
        setServiceStatus(SERVICE_STOPPED);
    } catch (DWORD dwError) {
        // Log the error.
        xlog::SysLogEvent(log_name, xlog::LogEvents::kError, dwError,
                          L"Stop Service");

        // Set the original service status.
        setServiceStatus(original_state);
    } catch (...) {
        // Log the error.
        xlog::SysLogEvent(log_name, xlog::LogEvents::kError, 0,
                          L"Service failed to stop.");

        // Set the original service status.
        setServiceStatus(original_state);
    }
}

//
//   FUNCTION: ServiceController::Start(DWORD, wchar_t* *)
//
//   PURPOSE: The function starts the service. It calls the OnStart
//   virtual function in which you can specify the actions to take when
//   the service starts. If an error occurs during the startup, the
//   error will be logged in the Application event log, and the service
//   will be stopped.
//
//   PARAMETERS:
//   * Argc   - number of command line arguments
//   * Argv - array of command line arguments
//
void ServiceController::Start(DWORD Argc, wchar_t** Argv) {
    if (!processor_) {
        XLOG::l.crit("Unbelievable, but process_ is nullptr");
        return;
    }

    // Register the handler function for the service
    status_handle_ =
        tgt::IsDebug()
            // we want to know what is happened with service in windows
            ? RegisterServiceCtrlHandlerEx(name_.get(), ServiceCtrlHandlerEx,
                                           nullptr)
            // in release we want to use safe method
            : RegisterServiceCtrlHandler(name_.get(), ServiceCtrlHandler);

    if (!status_handle_) {
        XLOG::l(XLOG::kStdio)("I cannot register damned handlers {}",
                              GetLastError());
        throw GetLastError();  // crash here - we have rights
        return;
    }
    XLOG::l.i("Service handlers registered");

    try {
        using namespace cma::cfg;
        // Tell SCM that the service is starting.
        setServiceStatus(SERVICE_START_PENDING);

        cap::Install();
        upgrade::UpgradeLegacy(upgrade::Force::no);

        // Perform service-specific initialization.
        processor_->startService();

        // Tell SCM that the service is started.
        setServiceStatus(SERVICE_RUNNING);

        cma::cfg::rm_lwa::Execute();

    } catch (DWORD dwError) {
        // Log the error.
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          dwError, L"Service Start");

        // Set the service status to be stopped.
        setServiceStatus(SERVICE_STOPPED, dwError);
    } catch (...) {
        // Log the error.
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          0, L"Service failed to start.");

        // Set the service status to be stopped.
        setServiceStatus(SERVICE_STOPPED);
    }
}

//
//   FUNCTION: ServiceController::Pause()
//
//   PURPOSE: The function pauses the service if the service supports
//   pause and continue. It calls the OnPause virtual function in which
//   you can specify the actions to take when the service pauses. If an
//   error occurs, the error will be logged in the Application event
//   log, and the service will become running.
//
void ServiceController::Pause() {
    if (!processor_) return;  // #TODO: trace, this is bad
    try {
        // Tell SCM that the service is pausing.
        setServiceStatus(SERVICE_PAUSE_PENDING);

        // Perform service-specific pause operations.
        processor_->pauseService();

        // Tell SCM that the service is paused.
        setServiceStatus(SERVICE_PAUSED);
    } catch (DWORD dwError) {
        // Log the error.
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          dwError, L"Service Pause");

        // Tell SCM that the service is still running.
        setServiceStatus(SERVICE_RUNNING);
    } catch (...) {
        // Log the error.
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          0, L"Service failed to pause.");

        // Tell SCM that the service is still running.
        setServiceStatus(SERVICE_RUNNING);
    }
}
//
//   FUNCTION: ServiceController::Continue()
//
//   PURPOSE: The function resumes normal functioning after being paused
//   if the service supports pause and continue. It calls the OnContinue
//   virtual function in which you can specify the actions to take when
//   the service continues. If an error occurs, the error will be logged
//   in the Application event log, and the service will still be paused.
//
void ServiceController::Continue() {
    try {
        // Tell SCM that the service is resuming.
        setServiceStatus(SERVICE_CONTINUE_PENDING);

        // Perform service-specific continue operations.
        processor_->continueService();

        // Tell SCM that the service is running.
        setServiceStatus(SERVICE_RUNNING);
    } catch (DWORD dwError) {
        // Log the error.
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          dwError, L"Service Continue");

        // Tell SCM that the service is still paused.
        setServiceStatus(SERVICE_PAUSED);
    } catch (...) {
        // Log the error.
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          0, L"Service failed to continue.");

        // Tell SCM that the service is still paused.
        setServiceStatus(SERVICE_PAUSED);
    }
}
//
//   FUNCTION: ServiceController::Shutdown()
//
//   PURPOSE: The function executes when the system is shutting down. It
//   calls the OnShutdown virtual function in which you can specify what
//   should occur immediately prior to the system shutting down. If an
//   error occurs, the error will be logged in the Application event
//   log.
//
void ServiceController::Shutdown() {
    try {
        // Perform service-specific shutdown operations.
        processor_->shutdownService();

        // Tell SCM that the service is stopped.
        setServiceStatus(SERVICE_STOPPED);
    } catch (DWORD dwError) {
        // Log the error.
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          dwError, L"Service Shutdown");
    } catch (...) {
        // Log the error.
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          0, L"Service failed to shutdown.");
    }
}

//
//   FUNCTION: ServiceController::ServiceCtrlHandler(DWORD)
//
//   PURPOSE: The function is called by the SCM whenever a control code
//   is sent to the service.
//
//   PARAMETERS:
//   * dwCtrlCode - the control code. This parameter can be one of the
//   following values:
//
//     SERVICE_CONTROL_CONTINUE
//     SERVICE_CONTROL_INTERROGATE
//     SERVICE_CONTROL_NETBINDADD
//     SERVICE_CONTROL_NETBINDDISABLE
//     SERVICE_CONTROL_NETBINDREMOVE
//     SERVICE_CONTROL_PARAMCHANGE
//     SERVICE_CONTROL_PAUSE
//     SERVICE_CONTROL_SHUTDOWN
//     SERVICE_CONTROL_STOP
//
//   This parameter can also be a user-defined control code ranges from
//   128 to 255.
//
void WINAPI ServiceController::ServiceCtrlHandler(DWORD control_code) {
    switch (control_code) {
        case SERVICE_CONTROL_STOP:
            s_controller_->Stop();
            break;
        case SERVICE_CONTROL_PAUSE:
            s_controller_->Pause();
            break;
        case SERVICE_CONTROL_CONTINUE:
            s_controller_->Continue();
            break;
        case SERVICE_CONTROL_SHUTDOWN:
            s_controller_->Shutdown();
            break;

        case SERVICE_CONTROL_INTERROGATE:
            break;
        default:
            break;
    }
}

DWORD WINAPI ServiceController::ServiceCtrlHandlerEx(DWORD control_code,
                                                     DWORD event_type,
                                                     void* event_data,
                                                     void* context) {
    XLOG::l.t("[----Control Code {:#X} Event Type {:#X}------]", control_code,
              event_type);

    switch (control_code) {
        case SERVICE_CONTROL_STOP:
            s_controller_->Stop();
            break;
        case SERVICE_CONTROL_PAUSE:
            s_controller_->Pause();
            break;
        case SERVICE_CONTROL_CONTINUE:
            s_controller_->Continue();
            break;
        case SERVICE_CONTROL_SHUTDOWN:
            s_controller_->Shutdown();
            break;

        case SERVICE_CONTROL_INTERROGATE:
            break;
        default:
            break;
    }
    return NO_ERROR;
}

// Window s specific performance counters
// Functions are from OWA/MSDN
// No exceptions
// C-like here to be more windows
namespace perf {

// read MULTI_SZ string from the registry
// #TODO gtest
std::vector<wchar_t> ReadPerfCounterKeyFromRegistry(PerfCounterReg type) {
    DWORD counters_size = 0;

    auto key = type == PerfCounterReg::national ? HKEY_PERFORMANCE_NLSTEXT
                                                : HKEY_PERFORMANCE_TEXT;

    // preflight
    ::RegQueryValueExW(key, L"Counter", nullptr, nullptr, nullptr,
                       &counters_size);
    if (counters_size == 0) {
        XLOG::l("Something is really wrong");
        return {};
    }

    // one char more
    std::vector<wchar_t> result(counters_size + 2 / sizeof(wchar_t));

    // actual read op
    ::RegQueryValueExW(key, L"Counter", nullptr, nullptr,
                       reinterpret_cast<LPBYTE>(result.data()), &counters_size);

    result[counters_size] = 0;  // to stop all possible strlens here

    return result;
}

// simple scanner of multi_sz strings
// #TODO gtest?
const wchar_t* GetMultiSzEntry(wchar_t*& Pos, const wchar_t* End) {
    auto sz = Pos;
    if (sz >= End) return nullptr;

    auto len = wcslen(sz);
    if (len == 0) return nullptr;  // last string in multi_sz

    Pos += len + 1;
    return sz;
}

std::optional<uint32_t> FindPerfIndexInRegistry(std::wstring_view Key) {
    if (Key.empty()) return {};

    for (auto reg_type : {PerfCounterReg::national, PerfCounterReg::english}) {
        auto counter_str =
            wtools::perf::ReadPerfCounterKeyFromRegistry(reg_type);
        auto data = counter_str.data();
        const auto end = counter_str.data() + counter_str.size();
        for (;;) {
            // get id
            auto potential_id = GetMultiSzEntry(data, end);
            if (!potential_id) break;

            // get name
            auto potential_name = GetMultiSzEntry(data, end);
            if (!potential_name) break;

            // check name
            if (Key == potential_name) {
                return cma::tools::ConvertToUint32(potential_id);
            }
        }
    }

    return {};
}

// read default ENGLISH registry entry and build map with
// id - name
NameMap GenerateNameMap() {
    using namespace wtools::perf;
    NameMap nm;
    auto counter_str = ReadPerfCounterKeyFromRegistry(PerfCounterReg::english);
    auto data = counter_str.data();
    const auto end = counter_str.data() + counter_str.size();
    for (;;) {
        // get id
        auto id_as_text = GetMultiSzEntry(data, end);
        if (!id_as_text) break;

        // get name
        auto potential_name = GetMultiSzEntry(data, end);
        if (!potential_name) break;

        // check name
        auto id = ::wcstol(id_as_text, nullptr, 10);
        if (id > 0) nm[id] = potential_name;
    }
    return nm;
}

// Low level API to access to performance data
// Code below is not clean
// #TODO refactor to normal CMK standard
inline auto FindFirstObject(const PERF_DATA_BLOCK* PerfDataBlock) {
    using namespace cma::tools;
    return static_cast<const PERF_OBJECT_TYPE*>(
        GetOffsetInBytes(PerfDataBlock, PerfDataBlock->HeaderLength));
}

inline auto FindNextObject(const PERF_OBJECT_TYPE* Object) {
    return reinterpret_cast<const PERF_OBJECT_TYPE*>((BYTE*)Object +
                                                     Object->TotalByteLength);
}

inline auto FirstCounter(const PERF_OBJECT_TYPE* Object) {
    return reinterpret_cast<const PERF_COUNTER_DEFINITION*>(
        (BYTE*)Object + Object->HeaderLength);
}

inline auto NextCounter(const PERF_COUNTER_DEFINITION* PerfCounter) {
    return reinterpret_cast<const PERF_COUNTER_DEFINITION*>(
        (BYTE*)PerfCounter + PerfCounter->ByteLength);
}

inline auto GetCounterBlock(PERF_INSTANCE_DEFINITION* Instance) {
    return reinterpret_cast<PERF_COUNTER_BLOCK*>((BYTE*)Instance +
                                                 Instance->ByteLength);
}

inline auto GetCounterBlock(const PERF_INSTANCE_DEFINITION* Instance) {
    return reinterpret_cast<const PERF_COUNTER_BLOCK*>((const BYTE*)Instance +
                                                       Instance->ByteLength);
}

inline auto FirstInstance(PERF_OBJECT_TYPE* Object) {
    return reinterpret_cast<PERF_INSTANCE_DEFINITION*>(
        (BYTE*)Object + Object->DefinitionLength);
}
inline auto FirstInstance(const PERF_OBJECT_TYPE* Object) {
    return reinterpret_cast<const PERF_INSTANCE_DEFINITION*>(
        (const BYTE*)Object + Object->DefinitionLength);
}

inline auto NextInstance(PERF_INSTANCE_DEFINITION* Instance) {
    return reinterpret_cast<PERF_INSTANCE_DEFINITION*>(
        (BYTE*)Instance + Instance->ByteLength +
        GetCounterBlock(Instance)->ByteLength);
}

inline auto NextInstance(const PERF_INSTANCE_DEFINITION* Instance) {
    return reinterpret_cast<const PERF_INSTANCE_DEFINITION*>(
        (const BYTE*)Instance + Instance->ByteLength +
        GetCounterBlock(Instance)->ByteLength);
}

// main reader from registry
// DataSequence is primitive wrapper over data buffer
// DataSequence takes ownership over buffer
DataSequence ReadPerformanceDataFromRegistry(
    const std::wstring& CounterName) noexcept {
    DWORD buf_size = 40000;
    BYTE* buffer = nullptr;

    while (1) {
        // allocation(a bit stupid, but we do not want to have STL inside
        // of very low level Windows calls
        try {
            buffer = new BYTE[buf_size];
        } catch (...) {
            return cma::tools::DataBlock<BYTE>();  // ups
        }

        DWORD type = 0;
        auto ret =
            ::RegQueryValueExW(HKEY_PERFORMANCE_DATA, CounterName.c_str(),
                               nullptr, &type, buffer, &buf_size);
        RegCloseKey(HKEY_PERFORMANCE_DATA);  // MSDN requirement

        if (ret == ERROR_SUCCESS) break;  // normal exit

        if (ret == ERROR_MORE_DATA) {
            buf_size *= 2;    // :)
            delete[] buffer;  // realloc part one
            continue;         // to be safe
        } else
            return {};
    }

    return DataSequence((int)buf_size, buffer);
}

const PERF_OBJECT_TYPE* FindPerfObject(const DataSequence& Db,
                                       DWORD counter_index) noexcept {
    auto data = Db.data_;
    auto max_offset = Db.len_;
    if (!data || !max_offset) return nullptr;

    auto data_block = reinterpret_cast<PERF_DATA_BLOCK*>(data);
    auto object = FindFirstObject(data_block);

    for (DWORD i = 0; i < data_block->NumObjectTypes; ++i) {
        // iterate to the object we requested since apparently there can be
        // more than that in the buffer returned
        if (object->ObjectNameTitleIndex == counter_index) {
            return object;
        } else {
            object = FindNextObject(object);
        }
    }
    return nullptr;
}

std::vector<const PERF_INSTANCE_DEFINITION*> GenerateInstances(
    const PERF_OBJECT_TYPE* Object) noexcept {
    if (Object->NumInstances <= 0L) return {};

    std::vector<const PERF_INSTANCE_DEFINITION*> result;
    try {
        result.reserve(Object->NumInstances);  // optimization

        auto instance = FirstInstance(Object);
        for (auto i = 0L; i < Object->NumInstances; ++i) {
            result.push_back(instance);
            instance = NextInstance(instance);
        }
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FLINE + " exception: '{}'", e.what());
    }
    return result;
}

std::vector<std::wstring> GenerateInstanceNames(
    const PERF_OBJECT_TYPE* Object) noexcept {
    // check for nothing
    if (Object->NumInstances <= 0L) return {};

    std::vector<std::wstring> result;
    try {
        result.reserve(Object->NumInstances);  // optimization
        auto instance = FirstInstance(Object);
        for (auto i = 0L; i < Object->NumInstances; ++i) {
            result.push_back(
                (LPCWSTR)((BYTE*)(instance) + instance->NameOffset));
            instance = NextInstance(instance);
        }
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FLINE + " disaster in names: '{}'", e.what());
    }
    return result;
}

// Instance less support
// DataBlock is filled when NumInstances below or equal 0
std::vector<const PERF_COUNTER_DEFINITION*> GenerateCounters(
    const PERF_OBJECT_TYPE* Object,
    const PERF_COUNTER_BLOCK*& DataBlock) noexcept {
    std::vector<const PERF_COUNTER_DEFINITION*> result;
    DataBlock = nullptr;
    try {
        result.reserve(Object->NumCounters);  // optimization

        auto counter = FirstCounter(Object);
        for (DWORD i = 0UL; i < Object->NumCounters; ++i) {
            result.push_back(counter);
            counter = NextCounter(counter);
        }

        // when object has no instances immediately after the counters
        // we have data block, ergo a code a bit strange
        if (Object->NumInstances <= 0)
            DataBlock = reinterpret_cast<const PERF_COUNTER_BLOCK*>(counter);
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FLINE + " disaster in instance less counters: '{}'",
                e.what());
    }
    return result;
}

// simplified version ignoring datablock
std::vector<const PERF_COUNTER_DEFINITION*> GenerateCounters(
    const PERF_OBJECT_TYPE* Object) noexcept {
    const PERF_COUNTER_BLOCK* block = nullptr;
    return perf::GenerateCounters(Object, block);
}

// used only in skype
// build map of the <id:name>
std::vector<std::wstring> GenerateCounterNames(const PERF_OBJECT_TYPE* Object,
                                               const NameMap& Map) {
    std::vector<std::wstring> result;
    auto counter = FirstCounter(Object);
    for (DWORD i = 0UL; i < Object->NumCounters; ++i) {
        auto iter = Map.find(counter->CounterNameTitleIndex);
        if (iter != Map.end()) {
            result.push_back(iter->second);
        } else {
            // not found in map
            result.push_back(std::to_wstring(counter->CounterNameTitleIndex));
        }

        counter = NextCounter(counter);
    }
    return result;
}

// Windows special  function to extract data
// Based on OWA => INVALID
// #TODO http://msdn.microsoft.com/en-us/library/aa373178%28v=vs.85%29.aspx
static uint64_t GetCounterValueFromBlock(
    const PERF_COUNTER_DEFINITION& Counter,
    const PERF_COUNTER_BLOCK* Block) noexcept {
    unsigned offset = Counter.CounterOffset;
    const auto data = cma::tools::GetOffsetInBytes(Block, offset);

    constexpr const DWORD kPerfSizeMaks = 0x00000300;

    auto dwords = static_cast<const uint32_t*>(data);
    switch (Counter.CounterType & kPerfSizeMaks) {
        case PERF_SIZE_DWORD:
            return static_cast<uint64_t>(dwords[0]);
        case PERF_SIZE_LARGE:
            return *(UNALIGNED uint64_t*)data;
        case PERF_SIZE_ZERO:
            return 0;
        case PERF_SIZE_VARIABLE_LEN:
        default: {
            // handle other data generically. This is wrong in some
            // situation. Once upon a time in future we might implement a
            // conversion as described in
            // http://msdn.microsoft.com/en-us/library/aa373178%28v=vs.85%29.aspx
            int size = Counter.CounterSize;
            if (size == 4) return static_cast<uint64_t>(dwords[0]);

            if (size == 8) {
                // i am not sure that this must be should so complicated
                return static_cast<uint64_t>(dwords[0]) +
                       (static_cast<uint64_t>(dwords[1]) << 32);
            }

            // abnormal situation....
            return 0ULL;
        }
    }
}

std::vector<uint64_t> GenerateValues(
    const PERF_COUNTER_DEFINITION& Counter,
    std::vector<const PERF_INSTANCE_DEFINITION*>& Instances) noexcept {
    std::vector<uint64_t> result;
    try {
        if (Instances.size() > 0) {
            result.reserve(Instances.size());
            for (const auto instance : Instances) {
                auto counter_block = GetCounterBlock(instance);
                result.emplace_back(
                    GetCounterValueFromBlock(Counter, counter_block));
            }
        }
    } catch (const std::exception& e) {
        XLOG::l(XLOG_FLINE + " exception: '{}'", e.what());
        return {};
    }

    return result;
}

uint64_t GetValueFromBlock(const PERF_COUNTER_DEFINITION& Counter,
                           const PERF_COUNTER_BLOCK* Block) noexcept {
    if (Block) {
        return GetCounterValueFromBlock(Counter, Block);
    }
    return 0;
}

// from OWA
// #TODO gtest is required
std::string GetName(uint32_t CounterType) noexcept {
    // probably we need a map here
    // looks terrible
    switch (CounterType) {
        case PERF_COUNTER_COUNTER:
            return "counter";
        case PERF_COUNTER_TIMER:
            return "timer";
        case PERF_COUNTER_QUEUELEN_TYPE:
            return "queuelen_type";
        case PERF_COUNTER_BULK_COUNT:
            return "bulk_count";
        case PERF_COUNTER_TEXT:
            return "text";
        case PERF_COUNTER_RAWCOUNT:
            return "rawcount";
        case PERF_COUNTER_LARGE_RAWCOUNT:
            return "large_rawcount";
        case PERF_COUNTER_RAWCOUNT_HEX:
            return "rawcount_hex";
        case PERF_COUNTER_LARGE_RAWCOUNT_HEX:
            return "large_rawcount_HEX";
        case PERF_SAMPLE_FRACTION:
            return "sample_fraction";
        case PERF_SAMPLE_COUNTER:
            return "sample_counter";
        case PERF_COUNTER_NODATA:
            return "nodata";
        case PERF_COUNTER_TIMER_INV:
            return "timer_inv";
        case PERF_SAMPLE_BASE:
            return "sample_base";
        case PERF_AVERAGE_TIMER:
            return "average_timer";
        case PERF_AVERAGE_BASE:
            return "average_base";
        case PERF_AVERAGE_BULK:
            return "average_bulk";
        case PERF_100NSEC_TIMER:
            return "100nsec_timer";
        case PERF_100NSEC_TIMER_INV:
            return "100nsec_timer_inv";
        case PERF_COUNTER_MULTI_TIMER:
            return "multi_timer";
        case PERF_COUNTER_MULTI_TIMER_INV:
            return "multi_timer_inV";
        case PERF_COUNTER_MULTI_BASE:
            return "multi_base";
        case PERF_100NSEC_MULTI_TIMER:
            return "100nsec_multi_timer";
        case PERF_100NSEC_MULTI_TIMER_INV:
            return "100nsec_multi_timer_inV";
        case PERF_RAW_FRACTION:
            return "raw_fraction";
        case PERF_RAW_BASE:
            return "raw_base";
        case PERF_ELAPSED_TIME:
            return "elapsed_time";
        default: {
            char out[32];
            sprintf(out, "type(%X)", CounterType);
            return out;
        } break;
    }
}

}  // namespace perf

static std::mutex g_com_lock;                   // #VIP on start
static bool g_windows_com_initialized = false;  // #VIP on start

bool InitWindowsComSecurity() {  // Initialize
    auto hres =
        CoInitializeSecurity(nullptr,
                             -1,       // COM negotiates service
                             nullptr,  // Authentication services
                             nullptr,  // Reserved
                             RPC_C_AUTHN_LEVEL_DEFAULT,    // authentication
                             RPC_C_IMP_LEVEL_IMPERSONATE,  // Impersonation
                             nullptr,    // Authentication info
                             EOAC_NONE,  // Additional capabilities
                             nullptr     // Reserved
        );

    if (hres == RPC_E_TOO_LATE) {
        XLOG::l.w(XLOG_FUNC + " win security TOO LATE");
        return true;
    }
    if (FAILED(hres)) {
        XLOG::l.crit(XLOG_FUNC + " win security error {:#X}",
                     static_cast<unsigned>(hres));
        return false;  // Program has failed.
    }

    XLOG::l.i("COM Initialized");

    return true;
}

void InitWindowsCom() {
    std::lock_guard lk(g_com_lock);
    if (g_windows_com_initialized) return;

    auto hres = CoInitializeEx(nullptr, COINIT_MULTITHREADED);

    // Use the MAKEWORD(lowbyte, highbyte) macro declared in Windef.h
    auto wVersionRequested = MAKEWORD(2, 2);
    WSADATA wsaData{0};
    int err = WSAStartup(wVersionRequested, &wsaData);
    if (err != 0) {
        // Tell the user that we could not find a usable Winsock DLL.
        XLOG::l.crit("WSAStartup failed with error: {:#X}\n",
                     static_cast<unsigned>(err));
        return;
    }

    if (FAILED(hres)) {
        XLOG::l.crit("Can't init COM {:#X}", static_cast<unsigned>(hres));
        return;
    }
    auto ret = InitWindowsComSecurity();
    if (!ret) {
        XLOG::l.crit("Can't init COM SECURITY ");
        CoUninitialize();
        return;
    }

    XLOG::l.i("COM initialized");

    g_windows_com_initialized = true;
}

void CloseWindowsCom() {
    std::lock_guard lk(g_com_lock);
    if (!g_windows_com_initialized) return;
    CoUninitialize();
    XLOG::l.i("COM closed");
    g_windows_com_initialized = false;
}

bool IsWindowsComInitialized() {
    std::lock_guard lk(g_com_lock);
    return g_windows_com_initialized;
}

// # TODO gtest[-]
bool WmiObjectContains(IWbemClassObject* object, const std::wstring& name) {
    if (!object) {
        XLOG::l.crit(XLOG_FUNC + "Bad Parameter");
        return false;
    }

    VARIANT value;
    HRESULT res = object->Get(name.c_str(), 0, &value, nullptr, nullptr);
    if (FAILED(res)) return false;

    ON_OUT_OF_SCOPE(VariantClear(&value));
    return value.vt != VT_NULL;
}

std::wstring WmiGetWstring(const VARIANT& Var) {
    if (Var.vt & VT_ARRAY) {
        return L"<array>";
    }
    if (Var.vt & VT_VECTOR) {
        return L"<vector>";
    }

    switch (Var.vt) {
        case VT_BSTR:
            return std::wstring(Var.bstrVal);
        case VT_R4:
            return std::to_wstring(Var.fltVal);
        case VT_R8:
            return std::to_wstring(Var.dblVal);
        case VT_I1:
        case VT_I2:
        case VT_I4:
            // extremely dumb method to get always positive
            return std::to_wstring(WmiGetInt64_KillNegatives(Var));
        case VT_UI1:
        case VT_UI2:
        case VT_UI4:
            return std::to_wstring(WmiGetUint32(Var));

        case VT_UI8:
            return std::to_wstring(Var.ullVal);

        case VT_BOOL:
            return std::to_wstring(Var.boolVal ? true : false);

        case VT_NULL:
            return L"";

        default:
            XLOG::l.crit("Unknown data type in Vector [{}]", Var.vt);
            return L"";
    }
}

std::wstring WmiStringFromObject(IWbemClassObject* object,
                                 const std::vector<std::wstring>& names,
                                 std::wstring_view separator) {
    std::wstring result;
    for (auto& name : names) {
        // data
        VARIANT value;

        // clearing of the value
        memset(&value, 0,
               sizeof(value));  // prevents potential usage
                                // of the non-initialized data
                                // when converting I4 to UI4
        // Get the value of the Name property
        auto hres = object->Get(name.c_str(), 0, &value, nullptr, nullptr);
        if (SUCCEEDED(hres)) {
            ON_OUT_OF_SCOPE(VariantClear(&value));
            auto str = wtools::WmiGetWstring(value);
            if (str[0] == '-') {
                XLOG::t("WMI Negative value '{}' [{}], type [{}]",
                        ConvertToUTF8(name), ConvertToUTF8(str), value.vt);
            }
            result += str;
            result += separator;
        }
    }
    if (result.empty()) {
        XLOG::d("We have empty result for wbm_object, this is unusual");
        return {};
    }

    result.pop_back();  // remove last L","
    return result;
}

// optimized versions
std::wstring WmiStringFromObject(IWbemClassObject* Object,
                                 const std::wstring& Name) {
    // data
    VARIANT value;
    // Get the value of the Name property
    auto hres = Object->Get(Name.c_str(), 0, &value, nullptr, nullptr);
    if (FAILED(hres)) return {};

    ON_OUT_OF_SCOPE(VariantClear(&value));
    return wtools::WmiGetWstring(value);
}

// optimized version
std::optional<std::wstring> WmiTryGetString(IWbemClassObject* Object,
                                            const std::wstring& Name) {
    // data
    VARIANT value;
    // Get the value of the Name property
    auto hres = Object->Get(Name.c_str(), 0, &value, nullptr, nullptr);
    if (FAILED(hres)) return {};

    ON_OUT_OF_SCOPE(VariantClear(&value));
    if (value.vt == VT_NULL) return {};
    return wtools::WmiGetWstring(value);
}

uint64_t WmiUint64FromObject(IWbemClassObject* Object,
                             const std::wstring& Name) {
    // data
    VARIANT value;
    // Get the value of the Name property
    auto hres = Object->Get(Name.c_str(), 0, &value, nullptr, nullptr);
    if (FAILED(hres)) return 0;

    ON_OUT_OF_SCOPE(VariantClear(&value));
    if (value.vt == VT_NULL) return {};
    return wtools::WmiGetUint64(value);
}

// gtest
// returns name vector
// on error returns empty
std::vector<std::wstring> WmiGetNamesFromObject(IWbemClassObject* WmiObject) {
    SAFEARRAY* names = nullptr;
    HRESULT res = WmiObject->GetNames(
        nullptr, WBEM_FLAG_ALWAYS | WBEM_FLAG_NONSYSTEM_ONLY, nullptr, &names);
    if (FAILED(res) || nullptr == names) {
        XLOG::l.e("Failed to get names from WmiObject {:#X}", res);
        return {};  // Program has failed.
    }
    ON_OUT_OF_SCOPE(if (names)::SafeArrayDestroy(names););

    LONG start = 0;
    LONG end = 0;
    unsigned long hr = ::SafeArrayGetLBound(names, 1, &start);
    if (FAILED(hr)) {
        XLOG::l.e("Failed in Safe Array {:#X}", hr);
        return {};  // Program has failed.
    }

    hr = ::SafeArrayGetUBound(names, 1, &end);
    if (FAILED(hr)) {
        XLOG::l.e("Failed in Safe Array {:#X}", hr);
        return {};  // Program has failed.
    }

    std::vector<std::wstring> result;
    result.reserve(end - start + 1);

    for (auto i = start; i <= end; ++i) {
        BSTR property_name = nullptr;
        res = ::SafeArrayGetElement(names, &i, &property_name);
        if (FAILED(hr)) {
            XLOG::l.crit(
                "Failed Get Element From SafeArrat {:#X} {}/{}/{} + {}/{:#x}/{}",
                res,            // result
                i, start, end,  // indexes
                names->cLocks, names->fFeatures, names->cbElements);
            return {};  // Program has failed.
        }
        ON_OUT_OF_SCOPE(::SysFreeString(property_name));

        result.emplace_back(std::wstring(property_name));
    }

    return result;
}

// returns valid enumerator or nullptr
IEnumWbemClassObject* WmiExecQuery(IWbemServices* Services,
                                   const std::wstring& Query) noexcept {
    XLOG::t("Query is '{}'", ConvertToUTF8(Query));
    IEnumWbemClassObject* enumerator = nullptr;
    auto hres = Services->ExecQuery(
        bstr_t("WQL"),          // always the same
        bstr_t(Query.c_str()),  // text of query
        WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY,  // legacy agent
        nullptr,                                                // nobody knows
        &enumerator);

    if (SUCCEEDED(hres)) return enumerator;
    // SHOULD NOT HAPPEN
    XLOG::l.e("Failed query wmi {:#X}, query is {}",
              static_cast<unsigned>(hres), ConvertToUTF8(Query));
    return nullptr;  // Program has failed.
}

bool WmiWrapper::open() noexcept {  // Obtain the initial locator to Windows
                                    // Management
                                    // on a particular host computer.
    std::lock_guard lk(lock_);
    IWbemLocator* locator = nullptr;

    auto hres =
        CoCreateInstance(CLSID_WbemLocator, nullptr, CLSCTX_INPROC_SERVER,
                         IID_IWbemLocator, reinterpret_cast<void**>(&locator));

    if (FAILED(hres)) {
        XLOG::l.crit("Can't Create Instance WMI {:#X}",
                     static_cast<unsigned long>(hres));
        return false;  // Program has failed.
    }
    locator_ = locator;
    return true;
}

// clean all
void WmiWrapper::close() noexcept {
    std::lock_guard lk(lock_);
    if (nullptr != locator_) {
        locator_->Release();
        locator_ = nullptr;
    }

    if (nullptr != services_) {
        services_->Release();
        services_ = nullptr;
    }
}

// connect to the WMI namespace, root\\Something
// returns true when connect succeed or connect exists
// thread safe
bool WmiWrapper::connect(const std::wstring& NameSpace) noexcept {
    if (NameSpace.empty()) {
        XLOG::l.crit(XLOG_FUNC + " nullptr!");
        return false;
    }
    std::lock_guard lk(lock_);
    if (nullptr == locator_) {
        XLOG::l.crit(XLOG_FUNC + " what about open before connect?");
        return false;
    }

    if (nullptr != services_) {
        XLOG::l.w(XLOG_FUNC + " already connected");
        return true;
    }

    // Connect to the root\cimv2 namespace with the
    // current user and obtain pointer pSvc
    // to make IWbemServices calls.
    // #TODO no user name and no password looks not good
    auto hres =
        locator_->ConnectServer(_bstr_t(NameSpace.c_str()),  // WMI namespace
                                nullptr,                     // User name
                                nullptr,                     // User password
                                nullptr,                     // Locale
                                0,                           // Security flags
                                nullptr,                     // Authority
                                nullptr,                     // Context object
                                &services_  // IWbemServices proxy
        );

    if (SUCCEEDED(hres)) return true;

    XLOG::l.e("Can't connect to the namespace {} {:#X}",
              ConvertToUTF8(NameSpace), static_cast<unsigned long>(hres));
    return false;  // Program has failed.
}

// This is OPTIONAL feature, LWA doesn't use it
bool WmiWrapper::impersonate() noexcept {
    std::lock_guard lk(lock_);
    if (nullptr == services_) {
        XLOG::l.e(XLOG_FUNC + " not connected");
        return false;
    }
    // Set the IWbemServices proxy so that impersonation
    // of the user (client) occurs.
    auto hres = CoSetProxyBlanket(

        services_,                    // the proxy to set
        RPC_C_AUTHN_WINNT,            // authentication service
        RPC_C_AUTHZ_NONE,             // authorization service
        nullptr,                      // Server principal name
        RPC_C_AUTHN_LEVEL_CALL,       // authentication level
        RPC_C_IMP_LEVEL_IMPERSONATE,  // impersonation level
        nullptr,                      // client identity
        EOAC_NONE                     // proxy capabilities
    );

    if (SUCCEEDED(hres)) return true;

    XLOG::l.e("Failed blanker/impersonation locator wmI {:X}", hres);
    return false;  // Program has failed.
}

// RETURNS RAW OBJECT
// returns nullptr, WmiStatus
std::tuple<IWbemClassObject*, WmiStatus> WmiGetNextObject(
    IEnumWbemClassObject* Enumerator) {
    if (nullptr == Enumerator) {
        XLOG::l.e("nullptr in Enumerator");
        return {nullptr, WmiStatus::error};
    }
    ULONG returned = 0;
    IWbemClassObject* wmi_object = nullptr;

    auto timeout = cma::cfg::groups::global.getWmiTimeout();
    auto hres = Enumerator->Next(timeout * 1000, 1, &wmi_object,
                                 &returned);  // legacy code
    if (WBEM_S_TIMEDOUT == hres) {
        XLOG::l.e("Timeout [{}] seconds broken  when query WMI", timeout);
        return {nullptr, WmiStatus::timeout};
    }

    if (WBEM_S_FALSE == hres) return {nullptr, WmiStatus::ok};  // no more data
    if (WBEM_NO_ERROR != hres) {
        XLOG::l.t("Return {:#X} probably object doesn't exist",
                  static_cast<unsigned int>(hres));
        return {nullptr, WmiStatus::error};
    }

    if (0 == returned) return {nullptr, WmiStatus::ok};  // eof

    return {wmi_object, WmiStatus::ok};
}

static void FillAccuAndNames(std::wstring& accu,
                             std::vector<std::wstring>& names,
                             IWbemClassObject* wmi_object,
                             std::wstring_view separator) {
    if (names.empty()) {
        // we have asking for everything, ergo we have to use
        // get name list from WMI
        names = std::move(wtools::WmiGetNamesFromObject(wmi_object));
    }
    accu = cma::tools::JoinVector(names, separator);
    if (accu.empty()) {
        XLOG::l("Failed to get names");
    } else
        accu += L'\n';
}

// returns nullptr, WmiStatus
std::tuple<std::wstring, WmiStatus> WmiWrapper::produceTable(
    IEnumWbemClassObject* enumerator,
    const std::vector<std::wstring>& existing_names,
    std::wstring_view separator) noexcept {
    // preparation
    std::wstring accu;
    auto status_to_return = WmiStatus::ok;

    bool accu_is_empty = true;
    // setup default names vector
    auto names = existing_names;

    // processing loop
    while (nullptr != enumerator) {
        auto [wmi_object, status] = WmiGetNextObject(enumerator);
        status_to_return = status;  // last status is most important

        if (nullptr == wmi_object) break;
        ON_OUT_OF_SCOPE(wmi_object->Release());

        // init accu with names
        if (accu_is_empty) {
            FillAccuAndNames(accu, names, wmi_object, separator);
            accu_is_empty = false;
        }

        auto raw = wtools::WmiStringFromObject(wmi_object, names, separator);
        if (!raw.empty()) accu += raw + L"\n";
    }

    return {accu, status_to_return};
}

std::wstring WmiWrapper::makeQuery(const std::vector<std::wstring>& Names,
                                   const std::wstring& Target) noexcept {
    // build name_list string if any or assign "*"
    auto name_list = cma::tools::JoinVector(Names, L",");

    if (name_list.empty()) {
        name_list = L"*";
    }

    // build query itself
    std::wstring query_text = L"SELECT " + name_list + L" FROM " + Target;
    return query_text;
}

// work horse to ask certain names from the target
// returns "", Status
std::tuple<std::wstring, WmiStatus> WmiWrapper::queryTable(
    const std::vector<std::wstring>& names, const std::wstring& target,
    std::wstring_view separator) noexcept {
    auto query_text = makeQuery(names, target);

    // Send a query to system
    std::lock_guard lk(lock_);
    auto enumerator = wtools::WmiExecQuery(services_, query_text);

    // make a table using enumerator and supplied Names vector
    if (nullptr == enumerator) {
        XLOG::d("WMI enumerator is null for '{}'", ConvertToUTF8(target));
        return {std::wstring(), WmiStatus::error};
    }
    ON_OUT_OF_SCOPE(enumerator->Release());

    return produceTable(enumerator, names, separator);
}

// special purposes: formatting for PS for example
// on error returns nullptr
// Release MUST!!!
IEnumWbemClassObject* WmiWrapper::queryEnumerator(
    const std::vector<std::wstring>& Names,
    const std::wstring& Target) noexcept {
    auto query_text = makeQuery(Names, Target);

    // Send a query to system
    std::lock_guard lk(lock_);
    return wtools::WmiExecQuery(services_, query_text);
}

HMODULE LoadWindowsLibrary(const std::wstring& DllPath) {
    // this should be sufficient most of the time
    static const size_t buffer_size = 128;

    std::wstring dllpath_expanded;
    dllpath_expanded.resize(buffer_size, '\0');
    DWORD required =
        ExpandEnvironmentStringsW(DllPath.c_str(), &dllpath_expanded[0],
                                  static_cast<DWORD>(dllpath_expanded.size()));

    if (required > dllpath_expanded.size()) {
        dllpath_expanded.resize(required + 1);
        required = ExpandEnvironmentStringsW(
            DllPath.c_str(), &dllpath_expanded[0],
            static_cast<DWORD>(dllpath_expanded.size()));
    } else if (required == 0) {
        dllpath_expanded = DllPath;
    }
    if (required != 0) {
        // required includes the zero terminator
        dllpath_expanded.resize(required - 1);
    }

    // load the library as a datafile without loading referenced dlls. This
    // is quicker but most of all it prevents problems if dependent dlls
    // can't be loaded.
    return LoadLibraryExW(
        dllpath_expanded.c_str(), nullptr,
        DONT_RESOLVE_DLL_REFERENCES | LOAD_LIBRARY_AS_DATAFILE);
}

// Look into the registry in order to find out, which
// event logs are available
// return false only when something wrong with registry
std::vector<std::string> EnumerateAllRegistryKeys(const char* RegPath) {
    // Open Key for enumerating
    HKEY key = nullptr;
    DWORD r = ::RegOpenKeyExA(HKEY_LOCAL_MACHINE, RegPath, 0,
                              KEY_ENUMERATE_SUB_KEYS, &key);
    if (r != ERROR_SUCCESS) {
        XLOG::l(" Cannot open registry key '{}' error [{}]", RegPath,
                GetLastError());
        return {};
    }
    ON_OUT_OF_SCOPE(RegCloseKey(key));

    std::vector<std::string> entries;

    // Enumerate all sub keys
    constexpr int buf_len = 1024;
    for (DWORD i = 0; r == ERROR_SUCCESS || r == ERROR_MORE_DATA; ++i) {
        char key_name[buf_len];
        DWORD len = buf_len;
        r = ::RegEnumKeyExA(key, i, key_name, &len, nullptr, nullptr, nullptr,
                            nullptr);
        if (r == ERROR_NO_MORE_ITEMS) break;

        if (r != ERROR_SUCCESS) {
            XLOG::l("Failed to enum '{}' error [{}]", key_name, r);
            break;
        }
        entries.emplace_back(key_name);
    };
    return entries;
}

// gtest [+]
// returns data from the root machine registry
uint32_t GetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                          uint32_t dflt) noexcept {
    HKEY hkey = nullptr;
    auto ret = ::RegOpenKeyW(HKEY_LOCAL_MACHINE, path.data(), &hkey);
    if (ERROR_SUCCESS == ret && nullptr != hkey) {
        ON_OUT_OF_SCOPE(::RegCloseKey(hkey));
        DWORD type = REG_DWORD;
        uint32_t buffer = dflt;
        DWORD count = sizeof(buffer);
        ret = ::RegQueryValueExW(hkey, value_name.data(), nullptr, &type,
                                 reinterpret_cast<LPBYTE>(&buffer), &count);
        if (ret == ERROR_SUCCESS && 0 != count && type == REG_DWORD) {
            return buffer;
        }
    }
    // failure here
    XLOG::t.t(XLOG_FLINE + "Absent {}\\{} query [{}]", ConvertToUTF8(path),
              ConvertToUTF8(value_name), ret);
    return dflt;
}

bool DeleteRegistryValue(std::wstring_view path,
                         std::wstring_view value_name) noexcept {
    HKEY hkey = nullptr;
    auto ret = ::RegOpenKeyW(HKEY_LOCAL_MACHINE, path.data(), &hkey);
    if (ERROR_SUCCESS == ret && nullptr != hkey) {
        ON_OUT_OF_SCOPE(::RegCloseKey(hkey));
        ret = ::RegDeleteValue(hkey, value_name.data());
        if (ret == ERROR_SUCCESS) return true;
        if (ret == ERROR_FILE_NOT_FOUND) {
            XLOG::t.t(XLOG_FLINE + "No need to delete {}\\{}",
                      ConvertToUTF8(path), ConvertToUTF8(value_name));
            return true;
        }

        XLOG::l(XLOG_FLINE + "Failed to delete {}\\{} error [{}]",
                ConvertToUTF8(path), ConvertToUTF8(value_name), ret);
        return false;
    }
    //  here
    XLOG::t.t(XLOG_FLINE + "No need to delete {}\\{}", ConvertToUTF8(path),
              ConvertToUTF8(value_name));
    return true;
}

// returns true on success
bool SetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                      std::wstring_view value) {
    HKEY hKey;
    auto ret = RegCreateKeyEx(HKEY_LOCAL_MACHINE, path.data(), 0L, nullptr,
                              REG_OPTION_NON_VOLATILE, KEY_ALL_ACCESS, NULL,
                              &hKey, NULL);
    if (ERROR_SUCCESS != ret) return false;

    // Set full application path with a keyname to registry
    ret = RegSetValueEx(hKey, value_name.data(), 0, REG_SZ,
                        reinterpret_cast<const BYTE*>(value.data()),
                        static_cast<uint32_t>(value.size() * sizeof(wchar_t)));
    return ERROR_SUCCESS == ret;
}

// returns true on success
bool SetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                      uint32_t value) noexcept {
    auto ret = ::RegSetKeyValue(HKEY_LOCAL_MACHINE, path.data(),
                                value_name.data(), REG_DWORD, &value, 4);
    if (ret != 0) XLOG::d("Bad with reg set value {}", ret);

    return ret == ERROR_SUCCESS;
}

std::wstring GetRegistryValue(std::wstring_view path,
                              std::wstring_view value_name,
                              std::wstring_view dflt) noexcept {
    HKEY hkey = nullptr;
    auto result = ::RegOpenKeyW(HKEY_LOCAL_MACHINE, path.data(), &hkey);
    if (ERROR_SUCCESS != result || nullptr == hkey) {
        // failure here
        XLOG::t.t(XLOG_FLINE + "Cannot open Key '{}' query return code [{}]",
                  ConvertToUTF8(path), result);
        return dflt.data();
    }

    ON_OUT_OF_SCOPE(::RegCloseKey(hkey));
    DWORD type = REG_SZ;
    wchar_t buffer[512];
    DWORD count = sizeof(buffer);
    auto ret = ::RegQueryValueExW(hkey, value_name.data(), nullptr, &type,
                                  reinterpret_cast<LPBYTE>(buffer), &count);

    // check for errors
    auto type_ok = type == REG_SZ || type == REG_EXPAND_SZ;
    if (count == 0 || !type_ok) {
        // failure here
        XLOG::t.t(XLOG_FLINE + "Can't open '{}\\{}' query returns [{}]",
                  ConvertToUTF8(path), ConvertToUTF8(value_name), ret);
        return dflt.data();
    }

    if (ret == ERROR_SUCCESS) return buffer;

    if (ret == ERROR_MORE_DATA) {
        // realloc required
        DWORD type = REG_SZ;
        auto buffer_big = new wchar_t[count / sizeof(wchar_t) + 2];
        ON_OUT_OF_SCOPE(delete[] buffer_big);
        DWORD count = sizeof(count);
        ret = ::RegQueryValueExW(hkey, value_name.data(), nullptr, &type,
                                 reinterpret_cast<LPBYTE>(buffer_big), &count);

        // check for errors
        type_ok = type == REG_SZ || type == REG_EXPAND_SZ;
        if (count == 0 || !type_ok) {
            // failure here
            XLOG::t.t(XLOG_FLINE + "Absent {}\\{} query return [{}]",
                      ConvertToUTF8(path), ConvertToUTF8(value_name), ret);
            return dflt.data();
        }

        if (ret == ERROR_SUCCESS) return buffer_big;
    }

    // failure here
    XLOG::t.t(XLOG_FLINE + "Bad key {}\\{} query return [{}]",
              ConvertToUTF8(path), ConvertToUTF8(value_name), ret);
    return dflt.data();
}

// process terminators
bool KillProcess(uint32_t ProcessId, int Code) noexcept {
    auto handle = OpenProcess(PROCESS_TERMINATE, FALSE, ProcessId);
    if (nullptr == handle) {
        if (GetLastError() == 5) {
            XLOG::d("Cannot open process for termination ACCESS is DENIED'{}'",
                    ProcessId);
        }
        return true;
    }
    ON_OUT_OF_SCOPE(CloseHandle(handle));

    if (FALSE == TerminateProcess(handle, Code)) {
        // - we have no problem(process already dead) - ignore
        // - we have problem: either code is invalid or something wrong
        // with Windows in all cases just report
        XLOG::d("Cannot terminate process '{}' gracefully, error [{}]",
                ProcessId, GetLastError());
    }

    return true;
}

// process terminator
// used to kill OpenHardwareMonitor
bool KillProcess(std::wstring_view process_name, int exit_code) noexcept {
    auto snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPALL, NULL);
    if (snapshot == nullptr) return false;

    auto current_process_id = GetCurrentProcessId();

    ON_OUT_OF_SCOPE(CloseHandle(snapshot));

    PROCESSENTRY32 entry32;
    entry32.dwSize = sizeof(entry32);
    auto result = Process32First(snapshot, &entry32);
    while (0 != result) {
        if (cma::tools::IsEqual(std::wstring_view(entry32.szExeFile),
                                process_name) &&
            (entry32.th32ProcessID != current_process_id)) {
            auto process =
                OpenProcess(PROCESS_TERMINATE, 0, entry32.th32ProcessID);
            if (nullptr != process) {
                TerminateProcess(process, exit_code);
                CloseHandle(process);
            }
        }
        result = Process32Next(snapshot, &entry32);
    }

    return true;
}

//
std::string StatusColumnText(StatusColumn exception_column) noexcept {
    switch (exception_column) {
        case StatusColumn::ok:
            return "OK";
        case StatusColumn::timeout:
            return "Timeout";
    }

    return "Undefined";
}

static std::string MakeWmiTailForName(char separator) noexcept {
    std::string value;
    value += separator;
    return value + "WMIStatus\n";
}

static std::string MakeWmiTailForData(StatusColumn status_column,
                                      char separator) noexcept {
    std::string value;
    value += separator;
    return value + StatusColumnText(status_column) + "\n";
}

// adds to the output Table from the WMI WMIStatus column
// column value is either Timeout or OK
// Before
// Name,Freq
// Total,1500
// AFter
// Name,Freq,WMIStatus
// Total, 500, OK
// Empty or quite short strings are replaced with WMIStatus\nTimeout\n
std::string WmiPostProcess(const std::string& in, StatusColumn status_column,
                           char separator) {
    if (in.size() < 5) {  // 5 is meaningless, just anything low
        // error and cached data absent
        return "WMIStatus\nTimeout\n";
    }

    // Tails' values
    auto tail_for_names = MakeWmiTailForName(separator);
    auto tail_for_data = MakeWmiTailForData(status_column, separator);

    // make valid array of lines
    auto table = cma::tools::SplitString(in, "\n");

    // names(header)
    table[0] += tail_for_names;

    // data(body), first line of the table is skipped
    std::transform(table.begin() + 1, table.end(), table.begin() + 1,
                   [tail_for_data](const std::string& value) {
                       return value + tail_for_data;
                   });

    return std::accumulate(table.begin(), table.end(), std::string());
}

// returns false only when something is really bad
// based on ToolHelp api family
// normally require elevation
// if op returns false, scan will be stopped(this is only optimization)
bool ScanProcessList(std::function<bool(const PROCESSENTRY32&)> op) {
    auto snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPALL, NULL);
    if (snapshot == nullptr) return false;
    ON_OUT_OF_SCOPE(::CloseHandle(snapshot));

    auto current_process_id = ::GetCurrentProcessId();

    // scan...
    PROCESSENTRY32 entry32;
    entry32.dwSize = sizeof(entry32);
    auto result = ::Process32First(snapshot, &entry32);
    while (result != 0) {
        if ((entry32.th32ProcessID != current_process_id)) {
            if (!op(entry32)) return true;  // break on false returned
        }
        result = ::Process32Next(snapshot, &entry32);
    }

    return true;
}

// finds all process and kills them with all their children
bool KillProcessFully(const std::wstring& process_name,
                      int exit_code) noexcept {
    std::vector<DWORD> processes_to_kill;
    auto name = process_name;
    cma::tools::WideLower(name);
    ScanProcessList(
        [&processes_to_kill, name](const PROCESSENTRY32& entry) -> bool {
            std::wstring incoming_name = entry.szExeFile;
            cma::tools::WideLower(incoming_name);
            if (name == incoming_name)
                processes_to_kill.push_back(entry.th32ProcessID);
            return true;
        });

    for (auto proc_id : processes_to_kill) {
        KillProcessTree(proc_id);
        KillProcess(proc_id, exit_code);
    }

    return true;
}

// finds all process and kills them with all their children
int FindProcess(std::wstring_view process_name) noexcept {
    std::vector<DWORD> processes_to_kill;
    int count = 0;
    std::wstring name(process_name);
    cma::tools::WideLower(name);
    ScanProcessList([&processes_to_kill, name,
                     &count](const PROCESSENTRY32& entry) -> bool {
        std::wstring incoming_name = entry.szExeFile;
        cma::tools::WideLower(incoming_name);
        if (name == incoming_name) count++;
        return true;
    });

    return count;
}

void KillProcessTree(uint32_t ProcessId) {
    // snapshot
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    ON_OUT_OF_SCOPE(CloseHandle(snapshot));

    // scan and kill
    // error management is ignored while this is secondary method for now
    PROCESSENTRY32 process;
    ZeroMemory(&process, sizeof(process));
    process.dwSize = sizeof(process);
    Process32First(snapshot, &process);
    do {
        // process.th32ProcessId is the PID.
        if (process.th32ParentProcessID == ProcessId) {
            KillProcess(process.th32ProcessID);
        }

    } while (Process32Next(snapshot, &process));
}

std::wstring GetArgv(uint32_t index) noexcept {
    int n_args = 0;
    auto argv = ::CommandLineToArgvW(GetCommandLineW(), &n_args);

    if (argv == nullptr) return {};

    ON_OUT_OF_SCOPE(::LocalFree(argv));

    if (index < static_cast<uint32_t>(n_args)) return argv[index];

    return {};
}

std::wstring GetCurrentExePath() noexcept {
    namespace fs = std::filesystem;

    std::wstring exe_path;
    int args_count = 0;
    auto arg_list = ::CommandLineToArgvW(GetCommandLineW(), &args_count);
    if (nullptr == arg_list) return {};

    ON_OUT_OF_SCOPE(::LocalFree(arg_list););
    fs::path exe = arg_list[0];

    std::error_code ec;
    if (fs::exists(exe, ec)) return exe.parent_path();
    xlog::l("Impossible exception: [%d] %s", ec.value(), ec.message());

    return {};
}

size_t GetOwnVirtualSize() noexcept {
#if defined(_WIN32)
    PROCESS_MEMORY_COUNTERS_EX pmcx = {};
    pmcx.cb = sizeof(pmcx);
    ::GetProcessMemoryInfo(GetCurrentProcess(),
                           reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&pmcx),
                           pmcx.cb);

    return pmcx.WorkingSetSize;
#else
#error "Not implemented"
    return 0;
#endif
}

namespace monitor {
bool IsAgentHealthy() noexcept {
    return GetOwnVirtualSize() < kMaxMemoryAllowed;
}
}  // namespace monitor

// Low level function to get parent reliable
uint32_t GetParentPid(uint32_t pid)  // By Napalm @ NetCore2K
{
    ULONG_PTR pbi[6];
    ULONG ulSize = 0;
    LONG(WINAPI * NtQueryInformationProcess)
    (HANDLE ProcessHandle, ULONG ProcessInformationClass,
     PVOID ProcessInformation, ULONG ProcessInformationLength,
     PULONG ReturnLength);
    *(FARPROC*)&NtQueryInformationProcess =
        GetProcAddress(LoadLibraryA("NTDLL.DLL"), "NtQueryInformationProcess");
    if (!NtQueryInformationProcess) return 0;

    auto h = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pid);
    if (h == 0) {
        XLOG::l.w("Can't get info from process [{}] error [{}]", pid,
                  GetLastError());

        return 0;
    }
    ON_OUT_OF_SCOPE(CloseHandle(h));

    if (NtQueryInformationProcess(h, 0, &pbi, sizeof(pbi), &ulSize) >= 0 &&
        ulSize == sizeof(pbi))
        return (uint32_t)(pbi[5]);

    return 0;
}

#define READ_PERMISSIONS (FILE_READ_DATA | FILE_READ_ATTRIBUTES)
#define WRITE_PERMISSIONS \
    (FILE_WRITE_DATA | FILE_APPEND_DATA | FILE_WRITE_ATTRIBUTES | FILE_WRITE_EA)
#define EXECUTE_PERMISSIONS (FILE_READ_DATA | FILE_EXECUTE)

// Constructor
ACLInfo::ACLInfo(_bstr_t bstrPath) {
    ace_list_ = nullptr;
    path_ = bstrPath;
}

// Destructor
ACLInfo::~ACLInfo(void) {
    // Free ace_list structure
    clearAceList();
}

// Free the nodes of ace_list
void ACLInfo::clearAceList() {
    AceList* pList = ace_list_;
    AceList* pNext;
    while (nullptr != pList) {
        pNext = pList->next;
        free(pList);
        pList = pNext;
    }

    ace_list_ = nullptr;
}

HRESULT ACLInfo::query() {
    BOOL success = TRUE;
    BYTE* security_descriptor_buffer = nullptr;
    DWORD size_needed = 0;

    // clear any previously queried information
    clearAceList();

    // Find out size of needed buffer for security descriptor with DACL
    // DACL = Discretionary Access Control List
    success = GetFileSecurityW((BSTR)path_, DACL_SECURITY_INFORMATION, nullptr,
                               0, &size_needed);

    if (0 == size_needed) {
        return E_FAIL;
    }
    security_descriptor_buffer = new BYTE[size_needed];

    // Retrieve security descriptor with DACL information
    success =
        GetFileSecurityW((BSTR)path_, DACL_SECURITY_INFORMATION,
                         security_descriptor_buffer, size_needed, &size_needed);

    // Check if we successfully retrieved security descriptor with DACL
    // information
    if (!success) {
        DWORD error = GetLastError();
        XLOG::l("Failed to get file security information {}", error);
        return E_FAIL;
    }

    // Getting DACL from Security Descriptor
    PACL acl = nullptr;
    BOOL bDaclPresent = FALSE;
    BOOL bDaclDefaulted = FALSE;
    success = GetSecurityDescriptorDacl(
        (SECURITY_DESCRIPTOR*)security_descriptor_buffer, &bDaclPresent, &acl,
        &bDaclDefaulted);

    // Check if we successfully retrieved DACL
    if (!success) {
        auto error = GetLastError();
        XLOG::l("Failed to retrieve DACL from security descriptor {}", error);
        return E_FAIL;
    }

    // Check if DACL present in security descriptor
    if (!bDaclPresent) {
        XLOG::l("DACL was not found.");
        return E_FAIL;
    }

    // DACL for specified file was retrieved successfully
    // Now, we should fill in the linked list of ACEs
    // Iterate through ACEs (Access Control Entries) of DACL
    for (USHORT i = 0; i < acl->AceCount; i++) {
        void* ace = nullptr;
        success = GetAce(acl, i, &ace);
        if (!success) {
            DWORD error = GetLastError();
            XLOG::l("Failed to get ace {}, {}", i, error);
            continue;
        }
        HRESULT hr = addAceToList((ACE_HEADER*)ace);
        if (FAILED(hr)) {
            XLOG::l("Failed to add ace {} to list", i);
            continue;
        }
    }
    return S_OK;
}

HRESULT ACLInfo::addAceToList(ACE_HEADER* Ace) {
    AceList* new_ace = (AceList*)malloc(sizeof(AceList));  // SK: from example
    if (nullptr == new_ace) {
        return E_OUTOFMEMORY;
    }

    // Check Ace type and update new list entry accordingly
    switch (Ace->AceType) {
        case ACCESS_ALLOWED_ACE_TYPE: {
            new_ace->allowed = TRUE;
            break;
        }
        case ACCESS_DENIED_ACE_TYPE: {
            new_ace->allowed = FALSE;
            break;
        }
    }
    // Update the remaining fields
    // We add new entry to the head of list
    new_ace->ace = Ace;
    new_ace->next = ace_list_;

    ace_list_ = new_ace;

    return S_OK;
}

static std::string MakeReadableString(bool allowed, const std::string& domain,
                                      const std::string& name,
                                      ACCESS_MASK mask_permissions) {
    std::string os;
    // Output Account info (in NT4 style: domain\user)
    if (allowed) {
        os += "Allowed to: ";
    } else {
        os += "Denied from: ";
    }

    if (!domain.empty()) {
        os += domain;
        os += "\\";
    }
    if (!name.empty()) {
        os += name;
    }

    // Output permissions (Read/Write/Execute)
    os += " [";

    // For Allowed aces
    if (allowed) {
        // Read Permissions
        if ((mask_permissions & READ_PERMISSIONS) == READ_PERMISSIONS) {
            os += "R";
        } else {
            os += " ";
        }
        // Write permissions
        if ((mask_permissions & WRITE_PERMISSIONS) == WRITE_PERMISSIONS) {
            os += "W";
        } else {
            os += " ";
        }
        // Execute Permissions
        if ((mask_permissions & EXECUTE_PERMISSIONS) == EXECUTE_PERMISSIONS) {
            os += "X";
        } else {
            os += " ";
        }
    } else
    // Denied Ace permissions
    {
        // Read Permissions
        if ((mask_permissions & READ_PERMISSIONS) != 0) {
            os += "R";
        } else {
            os += " ";
        }
        // Write permissions
        if ((mask_permissions & WRITE_PERMISSIONS) != 0) {
            os += "W";
        } else {
            os += " ";
        }
        // Execute Permissions
        if ((mask_permissions & EXECUTE_PERMISSIONS) != 0) {
            os += "X";
        } else {
            os += " ";
        }
    }
    os += "]";
    return os;
}

// code below has not very high quality
// copy pasted from MSDN
std::string ACLInfo::output() {
    if (nullptr == ace_list_) return "No ACL Info\n";

    ACE_HEADER* ace = nullptr;
    SID* ace_sid = nullptr;
    ACCESS_MASK mask_permissions = 0;
    auto list = ace_list_;
    // Iterate through ACEs list and
    // out put information
    std::string os;
    while (nullptr != list) {
        {
            ace = list->ace;
            if (list->allowed) {
                auto allowed = reinterpret_cast<ACCESS_ALLOWED_ACE*>(ace);
                ace_sid = (SID*)(&(allowed->SidStart));
                mask_permissions = allowed->Mask;
            } else {
                auto denied = reinterpret_cast<ACCESS_DENIED_ACE*>(ace);
                ace_sid = (SID*)(&(denied->SidStart));
                mask_permissions = denied->Mask;
            }
        }

        SID_NAME_USE sid_name_use;
        char name_buffer[MAX_PATH];
        char domain_buffer[MAX_PATH];
        DWORD name_len = sizeof(name_buffer);
        DWORD domain_name_len = sizeof(domain_buffer);

        // Get account name for SID
        auto ret =
            LookupAccountSidA(nullptr, ace_sid, name_buffer, &name_len,
                              domain_buffer, &domain_name_len, &sid_name_use);
        if (!ret) {
            XLOG::l("Failed to get account for SID");
            continue;
        }

        os += MakeReadableString(list->allowed, domain_buffer, name_buffer,
                                 mask_permissions);
        os += "\n";

        list = list->next;
    }
    return os;
}

std::string ReadWholeFile(const std::filesystem::path& fname) noexcept {
    try {
        std::ifstream f(fname.u8string(), std::ios::binary);

        if (!f.good()) {
            return {};
        }

        f.seekg(0, std::ios::end);
        auto fsize = static_cast<uint32_t>(f.tellg());

        // read contents
        f.seekg(0, std::ios::beg);
        std::string v;
        v.resize(fsize);
        f.read(reinterpret_cast<char*>(v.data()), fsize);
        return v;
    } catch (const std::exception& e) {
        // catching possible exceptions in the
        // ifstream or memory allocations
        XLOG::l(XLOG_FUNC + "Exception '{}' generated in read file", e.what());
        return {};
    }
    return {};
}

bool PatchFileLineEnding(const std::filesystem::path& fname) noexcept {
    auto result = ReadWholeFile(fname);
    if (result.empty()) return false;

    try {
        std::ofstream tst(fname.u8string());  // text file
        tst.write(result.c_str(), result.size());
        return true;
    } catch (const std::exception& e) {
        XLOG::l("Error during patching file line ending {}", e.what());
        return false;
    }
}

std::wstring GenerateRandomString(size_t max_length) noexcept {
    std::wstring possible_characters(
        L"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_#@$^&()[]{};:");

    std::random_device rd;
    std::mt19937 generator(rd());

    std::uniform_int_distribution<> dist(
        0, static_cast<int>(possible_characters.size()) - 1);
    std::wstring ret;
    for (size_t i = 0; i < max_length; i++) {
        int random_index = dist(generator);  // get index between 0 and
                                             // possible_characters.size()-1
        ret += possible_characters[random_index];
    }

    return ret;
}

static std::wstring CmaUserPrefix() noexcept {
    if (cma::IsService()) return L"cmk_in_";
    if (cma::IsTest()) return L"cmk_TST_";
    return {};
}

std::wstring GenerateCmaUserNameInGroup(std::wstring_view group) noexcept {
    if (group.empty()) return {};

    if (cma::IsService() || cma::IsTest()) {
        auto prefix = CmaUserPrefix();
        if (prefix.empty()) return {};

        return prefix + group.data();
    }

    return {};
}

InternalUser CreateCmaUserInGroup(const std::wstring& group) noexcept {
    uc::LdapControl primary_dc;

    auto g = wtools::ConvertToUTF8(group);

    // Set up the LOCALGROUP_INFO_1 structure.
    uc::Status add_group_status = uc::Status::exists;

    if (false) {
        wchar_t group_comment[] = L"Check MK Group created group";
        add_group_status = primary_dc.localGroupAdd(group, group_comment);
    }

    if (add_group_status == uc::Status::error) return {};

    auto name = GenerateCmaUserNameInGroup(group);
    if (name.empty()) return {};

    auto n = wtools::ConvertToUTF8(name);

    auto pwd = GenerateRandomString(12);

    primary_dc.userDel(name);
    auto add_user_status = primary_dc.userAdd(name, pwd);
    if (add_user_status != uc::Status::success) {
        XLOG::l("Can't add user '{}'", n);
        if (add_group_status == uc::Status::success)
            primary_dc.localGroupDel(group);
        return {};
    }

    // Now add the user to the local group.
    auto add_user_to_group_status =
        primary_dc.localGroupAddMembers(group, name);
    if (add_user_to_group_status != uc::Status::error) return {name, pwd};

    // Fail situation processing
    XLOG::l("Can't add user '{}' to group '{}'", n, g);
    if (add_user_status == uc::Status::success) primary_dc.userDel(name);

    if (add_group_status == uc::Status::success)
        primary_dc.localGroupDel(group);

    return {};
}

bool RemoveCmaUser(const std::wstring& user_name) noexcept {
    uc::LdapControl primary_dc;
    return primary_dc.userDel(user_name) != uc::Status::error;
}

bool ProtectPathFromUserWrite(const std::filesystem::path& path) {
    // CONTEXT: to prevent malicious file creation or modification  in folder
    // "programdata/checkmk" we must remove inherited write rights for
    // Users in checkmk root data folder.

    constexpr std::wstring_view command_templates[] = {
        L"icacls \"{}\" /inheritance:d /c",           // disable inheritance
        L"icacls \"{}\" /remove:g *S-1-5-32-545 /c",  // remove all user rights
        L"icacls \"{}\" /grant:r *S-1-5-32-545:(OI)(CI)(RX) /c"};  // read/exec

    for (auto const t : command_templates) {
        auto cmd = fmt::format(t.data(), path.wstring());
        if (!cma::tools::RunCommandAndWait(cmd)) {
            // logging is almost useless: at this phase logfile is absent
            XLOG::l.e("Failed command '{}'", wtools::ConvertToUTF8(cmd));
            return false;
        }
    }
    XLOG::l.i("User Write Protected '{}'", path.u8string());

    return true;
}

bool ProtectFileFromUserWrite(const std::filesystem::path& path) {
    // CONTEXT: to prevent malicious file creation or modification  in folder
    // "programdata/checkmk" we must remove inherited write rights for
    // Users in checkmk root data folder.

    constexpr std::wstring_view command_templates[] = {
        L"icacls \"{}\" /inheritance:d /c",           // disable inheritance
        L"icacls \"{}\" /remove:g *S-1-5-32-545 /c",  // remove all user rights
        L"icacls \"{}\" /grant:r *S-1-5-32-545:(RX) /c"};  // read/exec

    for (auto const t : command_templates) {
        auto cmd = fmt::format(t.data(), path.wstring());
        if (!cma::tools::RunCommandAndWait(cmd)) {
            // logging is almost useless: at this phase logfile is absent
            XLOG::l.e("Failed command '{}'", wtools::ConvertToUTF8(cmd));
            return false;
        }
    }
    XLOG::l.i("User Write Protected '{}'", path.u8string());

    return true;
}

bool ProtectPathFromUserAccess(const std::filesystem::path& entry) {
    // CONTEXT: some files must be protected from the user fully

    constexpr std::wstring_view command_templates[] = {
        L"icacls \"{}\" /inheritance:d /c",          // disable inheritance
        L"icacls \"{}\" /remove:g *S-1-5-32-545 /c"  // remove all user rights
    };

    for (auto const t : command_templates) {
        auto cmd = fmt::format(t.data(), entry.wstring());
        if (!cma::tools::RunCommandAndWait(cmd)) {
            // logging is almost useless: at this phase logfile is absent
            XLOG::l.e("Failed command '{}'", wtools::ConvertToUTF8(cmd));
            return false;
        }
    }
    XLOG::l.i("User Access Protected '{}'", entry.u8string());

    return true;
}

}  // namespace wtools

// verified code from the legacy client
// gtest is not required
inline SOCKET RemoveSocketInheritance(SOCKET OldSocket) {
    HANDLE new_handle = nullptr;

    ::DuplicateHandle(::GetCurrentProcess(),
                      reinterpret_cast<HANDLE>(OldSocket),
                      ::GetCurrentProcess(), &new_handle, 0, FALSE,
                      DUPLICATE_CLOSE_SOURCE | DUPLICATE_SAME_ACCESS);

    return reinterpret_cast<SOCKET>(new_handle);
}

//
// replaced WSASocketW in asio.hpp
// This is BAD method, still we have no other choice
//
SOCKET WSASocketW_Hook(int af, int type, int protocol,
                       LPWSAPROTOCOL_INFOW lpProtocolInfo, GROUP g,
                       DWORD dwFlags) {
    auto handle = ::WSASocketW(af, type, protocol, lpProtocolInfo, g, dwFlags);
    if (handle == INVALID_SOCKET) {
        XLOG::l.bp("Error on socket creation {}", GetLastError());
        return handle;
    }

    return RemoveSocketInheritance(handle);
}
