// Windows Tools
#include "stdafx.h"

#include "common/wtools.h"

#include <Psapi.h>
#include <WinSock2.h>
#include <comdef.h>
#include <fmt/format.h>
#include <fmt/xchar.h>
#include <sddl.h>
#include <shellapi.h>

#include <cstdint>
#include <fstream>
#include <numeric>
#include <random>
#include <string>

#include "common/wtools_runas.h"
#include "common/wtools_user_control.h"
#include "tools/_process.h"
#include "tools/_raii.h"
#include "wnx/cap.h"
#include "wnx/cfg.h"
#include "wnx/logger.h"
#pragma comment(lib, "wbemuuid.lib")
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "Sensapi.lib")
#pragma comment(lib, "iphlpapi.lib")

namespace fs = std::filesystem;
namespace rs = std::ranges;
using namespace std::chrono_literals;

namespace wtools {

bool ChangeAccessRights(
    const wchar_t *object_name,   // name of object
    SE_OBJECT_TYPE object_type,   // type of object
    const wchar_t *trustee_name,  // trustee for new ACE
    TRUSTEE_FORM trustee_form,    // format of trustee structure
    DWORD access_rights,          // access mask for new ACE
    ACCESS_MODE access_mode,      // type of ACE
    DWORD inheritance             // inheritance flags for new ACE ???
) {
    PACL old_dacl = nullptr;
    PSECURITY_DESCRIPTOR sd = nullptr;

    if (object_name == nullptr) {
        return false;
    }

    // Get a pointer to the existing DACL.
    auto result = ::GetNamedSecurityInfo(object_name, object_type,
                                         DACL_SECURITY_INFORMATION, nullptr,
                                         nullptr, &old_dacl, nullptr, &sd);
    if (ERROR_SUCCESS != result) {
        XLOG::l("GetNamedSecurityInfo Error {}", result);
        return false;
    }
    ON_OUT_OF_SCOPE(if (sd != nullptr)::LocalFree(sd));

    // Initialize an EXPLICIT_ACCESS structure for the new ACE.
    EXPLICIT_ACCESS ea;
    ZeroMemory(&ea, sizeof EXPLICIT_ACCESS);
    ea.grfAccessPermissions = access_rights;
    ea.grfAccessMode = access_mode;
    ea.grfInheritance = inheritance;
    ea.Trustee.TrusteeForm = trustee_form;
    ea.Trustee.ptstrName = const_cast<wchar_t *>(trustee_name);

    // Create a new ACL that merges the new ACE
    // into the existing DACL.
    PACL new_dacl = nullptr;
    result = ::SetEntriesInAcl(1, &ea, old_dacl, &new_dacl);
    if (ERROR_SUCCESS != result) {
        XLOG::l("SetEntriesInAcl Error {}", result);
        return false;
    }

    ON_OUT_OF_SCOPE(if (new_dacl != nullptr) LocalFree(new_dacl));

    // Attach the new ACL as the object's DACL.
    result = ::SetNamedSecurityInfo(const_cast<wchar_t *>(object_name),
                                    object_type, DACL_SECURITY_INFORMATION,
                                    nullptr, nullptr, new_dacl, nullptr);
    if (ERROR_SUCCESS != result) {
        XLOG::l("SetNamedSecurityInfo Error {}", result);
        return false;
    }

    return true;
}

std::pair<uint32_t, uint32_t> GetProcessExitCode(uint32_t pid) {
    const HANDLE h =
        ::OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (h == nullptr) {
        return {0, ::GetLastError()};
    }

    ON_OUT_OF_SCOPE(::CloseHandle(h));
    DWORD exit_code{0};
    if (::GetExitCodeProcess(h, &exit_code) == FALSE) {
        return {-1, ::GetLastError()};
    }

    return {exit_code, 0};
}

std::wstring GetProcessPath(uint32_t pid) noexcept {
    const HANDLE h =
        ::OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (h == nullptr) {
        return {};
    }
    ON_OUT_OF_SCOPE(::CloseHandle(h));

    if (wchar_t buffer[MAX_PATH];
        ::GetModuleFileNameEx(h, nullptr, buffer, MAX_PATH) != 0) {
        return buffer;
    }

    return {};
}

/// \b returns count of killed processes, -1 if dir is bad
int KillProcessesByDir(const fs::path &dir) noexcept {
    constexpr size_t minimum_path_len = 12;
    XLOG::d.i("Processing dir '{}'", dir);

    if (dir.wstring().size() < minimum_path_len) {
        // safety: we do not want to kill as admin something important
        return -1;
    }

    int killed_count = 0;

    ScanProcessList([dir, &killed_count](const PROCESSENTRY32W &entry) {
        const auto pid = entry.th32ProcessID;
        const auto exe = wtools::GetProcessPath(pid);
        if (exe.length() < minimum_path_len) {
            return ScanAction::advance;
        }

        fs::path p{exe};
        std::error_code ec;
        const auto shift = fs::relative(p, dir, ec).wstring();
        if (!ec && !shift.empty() && shift[0] != L'.') {
            XLOG::d.i("Killing process '{}'", p);
            KillProcess(pid, 99);
            killed_count++;
        }
        return ScanAction::advance;
    });

    return killed_count;
}

void KillProcessesByFullPath(const fs::path &path) noexcept {
    ScanProcessList([path](const PROCESSENTRY32W &entry) {
        const auto pid = entry.th32ProcessID;
        const auto exe = fs::path{GetProcessPath(pid)};

        if (exe == path) {
            XLOG::d.i("Killing process '{}'", exe);
            KillProcess(pid, 99);
        }
        return ScanAction::advance;
    });
}

namespace {
bool IsSameProcess(const PROCESSENTRY32W &entry, const fs::path &path_end,
                   uint32_t need_pid) noexcept {
    const auto pid = entry.th32ProcessID;
    const auto exe = fs::path{GetProcessPath(pid)};

    return (exe.wstring().ends_with(path_end.wstring()) || exe == path_end) &&
           (pid == need_pid);
}
}  // namespace

void KillProcessesByPathEndAndPid(const fs::path &path_end,
                                  uint32_t need_pid) noexcept {
    ScanProcessList([&](const PROCESSENTRY32W &entry) {
        if (!IsSameProcess(entry, path_end, need_pid)) {
            return ScanAction::advance;
        }
        XLOG::d.i("Killing process '{}' with pid {}", path_end, need_pid);
        KillProcess(need_pid, 99);
        return ScanAction::terminate;
    });
}

bool FindProcessByPathEndAndPid(const fs::path &path_end,
                                uint32_t need_pid) noexcept {
    bool found{false};
    ScanProcessList([&](const PROCESSENTRY32W &entry) {
        if (!IsSameProcess(entry, path_end, need_pid)) {
            return ScanAction::advance;
        }
        found = true;
        return ScanAction::terminate;
    });

    return found;
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

/// \b returns PID or 0,
uint32_t AppRunner::goExecAsJob(std::wstring_view command_line) noexcept {
    try {
        if (process_id_ != 0) {
            XLOG::l.bp("Attempt to reuse AppRunner");
            return 0;
        }

        prepareResources(command_line, true);

        auto [pid, jh, ph] = cma::tools::RunStdCommandAsJob(
            command_line.data(), cma::tools::InheritHandle::yes,
            stdio_.getWrite(), stderr_.getWrite(), 0, 0);
        // store data to reuse
        process_id_ = pid;
        job_handle_ = jh;
        process_handle_ = ph;

        // check and return on success
        if (process_id_ != 0) {
            return process_id_;
        }

        // failure s here
        XLOG::l(XLOG_FLINE + " Failed RunStd: [{}]*", GetLastError());

        cleanResources();

        return 0;
    } catch (const std::exception &e) {
        XLOG::l.crit(XLOG_FLINE + " unexpected exception: '{}'", e.what());
    }
    return 0;
}

uint32_t AppRunner::goExecAsJobAndUser(
    std::wstring_view user, std::wstring_view password,
    std::wstring_view command_line) noexcept {
    try {
        if (process_id_ != 0) {
            XLOG::l.bp("Attempt to reuse AppRunner");
            return 0;
        }

        prepareResources(command_line, true);

        auto [pid, jh, ph] =
            runas::RunAsJob(user, password, command_line.data(), TRUE,
                            stdio_.getWrite(), stderr_.getWrite());
        // store data to reuse
        process_id_ = pid;
        job_handle_ = jh;
        process_handle_ = ph;

        // check and return on success
        if (process_id_ != 0) {
            return process_id_;
        }

        // failure s here
        XLOG::l(XLOG_FLINE + " Failed RunStd: [{}]*", GetLastError());

        cleanResources();

        return 0;
    } catch (const std::exception &e) {
        XLOG::l.crit(XLOG_FLINE + " unexpected exception: '{}'", e.what());
    }
    return 0;
}

uint32_t AppRunner::goExec(std::wstring_view command_line,
                           UsePipe use_pipe) noexcept {
    try {
        if (process_id_ != 0) {
            XLOG::l.bp("Attempt to reuse AppRunner/updater");
            return 0;
        }
        prepareResources(command_line, use_pipe == UsePipe::yes);

        process_id_ = cma::tools::RunStdCommand(
                          command_line, cma::tools::WaitForEnd::no,
                          cma::tools::InheritHandle::yes, stdio_.getWrite(),
                          stderr_.getWrite(),
                          CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS, 0)
                          .value_or(0);
        if (process_id_ != 0) {
            return process_id_;
        }

        XLOG::l(XLOG_FLINE + " Failed updater RunStd: [{}]*", GetLastError());
        cleanResources();
        return 0;

    } catch (const std::exception &e) {
        XLOG::l.crit(XLOG_FLINE + " unexpected exception: '{}'", e.what());
    }
    return 0;
}

uint32_t AppRunner::goExecAsDetached(std::wstring_view command_line) noexcept {
    return goExec(command_line, UsePipe::yes);
}

uint32_t AppRunner::goExecAsController(
    std::wstring_view command_line) noexcept {
    return goExec(command_line, UsePipe::no);
}

std::mutex ServiceController::s_lock_;                          // NOLINT
ServiceController *ServiceController::s_controller_ = nullptr;  // NOLINT

// normal API
ServiceController::ServiceController(
    std::unique_ptr<wtools::BaseServiceProcessor> processor) {
    if (processor == nullptr) {
        XLOG::l.crit("Processor is nullptr");
        return;
    }
    std::lock_guard lk(s_lock_);
    if (processor_ == nullptr && s_controller_ == nullptr) {
        processor_ = std::move(processor);
        s_controller_ = this;
    }
}

void WINAPI ServiceController::ServiceMain(DWORD argc, wchar_t **argv) {
    // Register the handler function for the service
    XLOG::l.i("Service Main");
    s_controller_->Start(argc, argv);
}

// no return from here
// can print on screen
ServiceController::StopType ServiceController::registerAndRun(
    const wchar_t *service_name, bool can_stop, bool can_shutdown,
    bool can_pause_continue) {
    if (!processor_) {
        XLOG::l.bp("No processor");
        return StopType::fail;
    }
    if (service_name == nullptr) {
        XLOG::l.bp("No Service name");
        return StopType::fail;
    }

    // strange code below
    auto *allocated = new wchar_t[wcslen(service_name) + 1];
#pragma warning(push)
#pragma warning(disable : 4996)  //_CRT_SECURE_NO_WARNINGS
    wcscpy(allocated, service_name);
#pragma warning(pop)
    name_.reset(allocated);

    initStatus(can_stop, can_shutdown, can_pause_continue);

    const SERVICE_TABLE_ENTRY service_table[] = {{allocated, ServiceMain},
                                                 {nullptr, nullptr}};

    // Connects the main thread of a service process to the service
    // control manager, which causes the thread to be the service
    // control dispatcher thread for the calling process. This call
    // returns when the service has stopped. The process should simply
    // terminate when the call returns. Two words: Blocks Here
    try {
        if (::StartServiceCtrlDispatcher(service_table) == FALSE) {
            auto error = ::GetLastError();

            // this normal situation when we are starting service from
            // command line without parameters
            if (error == ERROR_FAILED_SERVICE_CONTROLLER_CONNECT) {
                return StopType::no_connect;
            }

            XLOG::l(XLOG::kStdio)
                .crit("Cannot Start Service '{}' error = [{}]",
                      ToUtf8(service_name), error);
            return StopType::fail;
        }
        return StopType::normal;
    } catch (const std::exception &e) {
        XLOG::l(XLOG::kStdio)
            .crit("Exception '{}' in Service start with error [{}]", e.what(),
                  ::GetLastError());
    } catch (...) {
        XLOG::l(XLOG::kStdio)
            .crit("Exception in Service start with error [{}]",
                  ::GetLastError());
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
bool InstallService(const wchar_t *service_name, const wchar_t *display_name,
                    uint32_t start_type, const wchar_t *dependencies,
                    const wchar_t *account, const wchar_t *password) {
    wchar_t service_path[MAX_PATH] = {0};
    XLOG::setup::ColoredOutputOnStdio(true);

    if (::GetModuleFileName(nullptr, service_path, ARRAYSIZE(service_path)) ==
        0) {
        XLOG::l(XLOG::kStdio)
            .crit("GetModuleFileName failed w/err {:#X}", GetLastError());
        return false;
    }

    // Open the local default service control manager database
    const SC_HANDLE service_manager = ::OpenSCManager(
        nullptr, nullptr, SC_MANAGER_CONNECT | SC_MANAGER_CREATE_SERVICE);

    if (service_manager == nullptr) {
        XLOG::l(XLOG::kStdio)
            .crit("OpenSCManager failed w/err {:#X}", GetLastError());
        return false;
    }

    ON_OUT_OF_SCOPE(CloseServiceHandle(service_manager););

    // Install the service into SCM by calling CreateService
    auto *service = ::CreateService(service_manager,       // SCManager database
                                    service_name,          // Name of service
                                    display_name,          // Name to display
                                    SERVICE_QUERY_STATUS,  // Desired access
                                    SERVICE_WIN32_OWN_PROCESS,  // Service type
                                    start_type,            // Service start type
                                    SERVICE_ERROR_NORMAL,  // Error control type
                                    service_path,          // Service's binary
                                    nullptr,       // No load ordering group
                                    nullptr,       // No tag identifier
                                    dependencies,  // Dependencies
                                    account,       // Service running account
                                    password       // Password of the account
    );
    if (service == nullptr) {
        auto error = GetLastError();
        if (error == ERROR_SERVICE_EXISTS) {
            XLOG::l(XLOG::kStdio)
                .crit("The Service '{}' already exists", ToUtf8(service_name));
            return false;
        }
        XLOG::l(XLOG::kStdio).crit("CreateService failed w/err {}", error);
    }
    ON_OUT_OF_SCOPE(CloseServiceHandle(service););

    XLOG::l(XLOG::kStdio)
        .i("The Service '{}' is installed.", ToUtf8(service_name));

    return true;
}

namespace {
void TryStopService(SC_HANDLE service, std::string_view name) {
    SERVICE_STATUS service_status = {};
    if (::ControlService(service, SERVICE_CONTROL_STOP, &service_status) !=
        TRUE) {
        XLOG::l(XLOG::kStdio)
            .i("\n{} is failed to stop [{}]", name, ::GetLastError());
    }

    XLOG::l(XLOG::kStdio).i("Stopping '{}'.", name);
    ::Sleep(1000);

    while (::QueryServiceStatus(service, &service_status) == TRUE) {
        if (service_status.dwCurrentState == SERVICE_STOP_PENDING) {
            xlog::sendStringToStdio(".");
            ::Sleep(1000);
        } else
            break;
    }

    if (service_status.dwCurrentState == SERVICE_STOPPED) {
        XLOG::l(XLOG::kStdio).i("\n{} is stopped.", name);
    } else {
        XLOG::l(XLOG::kStdio).i("\n{} failed to stop.", name);
    }
}

void LogLastError(std::string_view name) {
    auto e = ::GetLastError();
    if (e == ERROR_SERVICE_DOES_NOT_EXIST) {
        XLOG::l(XLOG::kStdio).crit("The Service '{}' doesn't exist", name);
        return;
    }

    XLOG::l(XLOG::kStdio).crit("OpenService '{}' failed, [{}]", name, e);
}
}  // namespace

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
bool UninstallService(const wchar_t *service_name,
                      UninstallServiceMode uninstall_mode) {
    XLOG::setup::ColoredOutputOnStdio(true);
    if (service_name == nullptr) {
        XLOG::l(XLOG::kStdio).crit("Parameter is null");
        return false;
    }
    auto name = ToUtf8(service_name);
    // Open the local default service control manager database
    const SC_HANDLE service_manager =
        ::OpenSCManager(nullptr, nullptr, SC_MANAGER_CONNECT);
    if (service_manager == nullptr) {
        XLOG::l(XLOG::kStdio)
            .crit("OpenSCManager failed, [{}]", GetLastError());
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(service_manager););

    // Open the service with delete, stop, and query status permissions
    const SC_HANDLE service =
        ::OpenService(service_manager, service_name,
                      SERVICE_STOP | SERVICE_QUERY_STATUS | DELETE);
    if (service == nullptr) {
        LogLastError(name);
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(service););

    if (uninstall_mode == UninstallServiceMode::normal) {
        TryStopService(service, name);
    }

    // Now remove the service by calling DeleteService.
    if (::DeleteService(service) == FALSE) {
        XLOG::l(XLOG::kStdio)
            .i("DeleteService for '{}' failed [{}]\n", name, ::GetLastError());
        return false;
    }

    XLOG::l(XLOG::kStdio)
        .i("The Service '{}' is successfully removed.\n", name);
    return true;
}

//
//   FUNCTION: ServiceController::setServiceStatus(DWORD, DWORD, DWORD)
//
//   PURPOSE: The function sets the service status and reports the
//   status to the SCM.
//
//   PARAMETERS:
//   * CurrentState - the state of the service
//   * Win32ExitCode - error code to report
//   * WaitHint - estimated time for pending operation, in milliseconds
//
void ServiceController::setServiceStatus(DWORD current_state,
                                         DWORD win32_exit_code,
                                         DWORD wait_hint) {
    static DWORD check_point = 1;
    status_.dwCurrentState = current_state;
    status_.dwWin32ExitCode = win32_exit_code;
    status_.dwWaitHint = wait_hint;

    status_.dwCheckPoint =
        current_state == SERVICE_RUNNING || current_state == SERVICE_STOPPED
            ? 0
            : check_point++;

    const auto ret = ::SetServiceStatus(status_handle_, &status_);
    XLOG::l.i("Setting service state {} result {}", current_state,
              ret != 0 ? 0 : GetLastError());
}

void ServiceController::initStatus(bool can_stop, bool can_shutdown,
                                   bool can_pause_continue) {
    status_.dwServiceType = SERVICE_WIN32_OWN_PROCESS;
    status_.dwCurrentState = SERVICE_START_PENDING;
    DWORD controls_accepted = 0;
    if (can_stop) {
        controls_accepted |= SERVICE_ACCEPT_STOP;
    }
    if (can_shutdown) {
        controls_accepted |= SERVICE_ACCEPT_SHUTDOWN;
    }
    if (can_pause_continue) {
        controls_accepted |= SERVICE_ACCEPT_PAUSE_CONTINUE;
    }
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
    if (processor_ == nullptr) {
        return;
    }

    const auto original_state = status_.dwCurrentState;
    const auto *log_name = processor_->getMainLogName();
    try {
        XLOG::l.i("Initiating stop routine...");
        setServiceStatus(SERVICE_STOP_PENDING);
        processor_->stopService(StopMode::cancel);
        processor_->cleanupOnStop();
        setServiceStatus(SERVICE_STOPPED);
    } catch (const DWORD &error_exception) {
        xlog::SysLogEvent(log_name, xlog::LogEvents::kError, error_exception,
                          L"Stop Service");
        setServiceStatus(original_state);
    } catch (...) {
        xlog::SysLogEvent(log_name, xlog::LogEvents::kError, 0,
                          L"Service failed to stop.");
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
//   * argc   - number of command line arguments
//   * argv - array of command line arguments
//
void ServiceController::Start(DWORD /*agc*/, wchar_t ** /*argv*/) {
    if (processor_ == nullptr) {
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

    if (status_handle_ == nullptr) {
        XLOG::l(XLOG::kStdio)("I cannot register damned handlers {}",
                              GetLastError());

        // crash here - we have rights
        throw ::GetLastError();  // NOLINT
    }
    XLOG::l.i("Service handlers registered");

    try {
        setServiceStatus(SERVICE_START_PENDING);
        processor_->startService();
        setServiceStatus(SERVICE_RUNNING);

    } catch (const DWORD &error_exception) {
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          error_exception, L"Service Start");
        setServiceStatus(SERVICE_STOPPED, error_exception, 0);
    } catch (...) {
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          0, L"Service failed to start.");
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
    if (processor_ == nullptr) {
        return;
    }
    try {
        // Tell SCM that the service is pausing.
        setServiceStatus(SERVICE_PAUSE_PENDING);

        // Perform service-specific pause operations.
        processor_->pauseService();

        // Tell SCM that the service is paused.
        setServiceStatus(SERVICE_PAUSED);
    } catch (const DWORD &error_exception) {
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          error_exception, L"Service Pause");

        // Tell SCM that the service is still running.
        setServiceStatus(SERVICE_RUNNING);
    } catch (...) {
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
    } catch (const DWORD &error_exception) {
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          error_exception, L"Service Continue");

        // Tell SCM that the service is still paused.
        setServiceStatus(SERVICE_PAUSED);
    } catch (...) {
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
        processor_->shutdownService(StopMode::cancel);
        setServiceStatus(SERVICE_STOPPED);
    } catch (const DWORD &error_exception) {
        xlog::SysLogEvent(processor_->getMainLogName(), xlog::LogEvents::kError,
                          error_exception, L"Service Shutdown");
    } catch (...) {
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
            [[fallthrough]];
        default:
            break;
    }
}

DWORD WINAPI ServiceController::ServiceCtrlHandlerEx(DWORD control_code,
                                                     DWORD event_type,
                                                     void * /*event_data*/,
                                                     void * /*context*/) {
    XLOG::d.t("[----Control Code {:#X} Event Type {:#X}------]", control_code,
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
            [[fallthrough]];
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

/// read MULTI_SZ string from the registry
std::vector<wchar_t> ReadPerfCounterKeyFromRegistry(PerfCounterReg type) {
    DWORD counters_size = 0;

    auto *key = type == PerfCounterReg::national ? HKEY_PERFORMANCE_NLSTEXT
                                                 : HKEY_PERFORMANCE_TEXT;

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

    result[counters_size] = 0;  // safety

    return result;
}

std::optional<uint32_t> FindPerfIndexInRegistry(std::wstring_view key) {
    if (key.empty()) {
        return {};
    }

    for (auto &&reg_type :
         {PerfCounterReg::national, PerfCounterReg::english}) {
        auto counter_str = ReadPerfCounterKeyFromRegistry(reg_type);
        auto *data = counter_str.data();
        const auto *end = counter_str.data() + counter_str.size();
        while (true) {
            auto *potential_id = GetMultiSzEntry(data, end);
            if (potential_id == nullptr) {
                break;
            }
            auto *potential_name = GetMultiSzEntry(data, end);
            if (potential_name == nullptr) {
                break;
            }

            // check name
            if (key == potential_name) {
                return cma::tools::ConvertToUint32(potential_id);
            }
        }
    }

    return {};
}

// read default ENGLISH registry entry and build map with
// id - name
NameMap GenerateNameMap() {
    NameMap nm;
    auto counter_str = ReadPerfCounterKeyFromRegistry(PerfCounterReg::english);
    auto *data = counter_str.data();
    const auto *end = counter_str.data() + counter_str.size();
    while (true) {
        // get id
        auto *id_as_text = GetMultiSzEntry(data, end);
        if (id_as_text == nullptr) {
            break;
        }

        // get name
        auto *potential_name = GetMultiSzEntry(data, end);
        if (potential_name == nullptr) {
            break;
        }

        // check name
        const auto id = ::wcstol(id_as_text, nullptr, 10);
        if (id > 0) {
            nm[id] = potential_name;
        }
    }
    return nm;
}

// Low level API to access to performance data
// Code below is not clean
// #TODO refactor to normal CMK standard
inline auto FindFirstObject(const PERF_DATA_BLOCK *PerfDataBlock) {
    return static_cast<const PERF_OBJECT_TYPE *>(cma::tools::GetOffsetInBytes(
        PerfDataBlock, PerfDataBlock->HeaderLength));
}

inline auto FindNextObject(const PERF_OBJECT_TYPE *Object) {
    return reinterpret_cast<const PERF_OBJECT_TYPE *>(
        reinterpret_cast<const BYTE *>(Object) + Object->TotalByteLength);
}

inline auto FirstCounter(const PERF_OBJECT_TYPE *Object) {
    return reinterpret_cast<const PERF_COUNTER_DEFINITION *>(
        reinterpret_cast<const BYTE *>(Object) + Object->HeaderLength);
}

inline auto NextCounter(const PERF_COUNTER_DEFINITION *PerfCounter) {
    return reinterpret_cast<const PERF_COUNTER_DEFINITION *>(
        reinterpret_cast<const BYTE *>(PerfCounter) + PerfCounter->ByteLength);
}

inline auto GetCounterBlock(PERF_INSTANCE_DEFINITION *Instance) {
    return reinterpret_cast<PERF_COUNTER_BLOCK *>(
        reinterpret_cast<BYTE *>(Instance) + Instance->ByteLength);
}

inline auto GetCounterBlock(const PERF_INSTANCE_DEFINITION *Instance) {
    return reinterpret_cast<const PERF_COUNTER_BLOCK *>(
        reinterpret_cast<const BYTE *>(Instance) + Instance->ByteLength);
}

inline auto FirstInstance(PERF_OBJECT_TYPE *Object) {
    return reinterpret_cast<PERF_INSTANCE_DEFINITION *>(
        reinterpret_cast<BYTE *>(Object) + Object->DefinitionLength);
}
inline auto FirstInstance(const PERF_OBJECT_TYPE *Object) {
    return reinterpret_cast<const PERF_INSTANCE_DEFINITION *>(
        reinterpret_cast<const BYTE *>(Object) + Object->DefinitionLength);
}

inline auto NextInstance(PERF_INSTANCE_DEFINITION *Instance) {
    return reinterpret_cast<PERF_INSTANCE_DEFINITION *>(
        reinterpret_cast<BYTE *>(Instance) + Instance->ByteLength +
        GetCounterBlock(Instance)->ByteLength);
}

inline auto NextInstance(const PERF_INSTANCE_DEFINITION *Instance) {
    return reinterpret_cast<const PERF_INSTANCE_DEFINITION *>(
        reinterpret_cast<const BYTE *>(Instance) + Instance->ByteLength +
        GetCounterBlock(Instance)->ByteLength);
}

// main reader from registry
// DataSequence is primitive wrapper over data buffer
// DataSequence takes ownership over buffer
DataSequence ReadPerformanceDataFromRegistry(
    const std::wstring &counter_name) noexcept {
    DWORD buf_size = 40000;
    BYTE *buffer = nullptr;

    while (true) {
        buffer = new BYTE[buf_size];

        DWORD type = 0;
        auto ret =
            ::RegQueryValueExW(HKEY_PERFORMANCE_DATA, counter_name.c_str(),
                               nullptr, &type, buffer, &buf_size);  // NOLINT
        // MSDN requirement
        ::RegCloseKey(HKEY_PERFORMANCE_DATA);  // NOLINT

        if (ret == ERROR_SUCCESS) {
            break;
        }

        if (ret != ERROR_MORE_DATA) {
            XLOG::l("Can't read counter '{}' error [{}]",
                    wtools::ToUtf8(counter_name), ret);
            return {};
        }

        buf_size *= 2;    // this is not optimal, may be reworked
        delete[] buffer;  // realloc part one
    }

    return {static_cast<int>(buf_size), buffer};
}

const PERF_OBJECT_TYPE *FindPerfObject(const DataSequence &data_buffer,
                                       DWORD counter_index) noexcept {
    auto *data = data_buffer.data_;
    const auto max_offset = data_buffer.len_;
    if (data == nullptr || max_offset == 0) {
        return nullptr;
    }

    const auto *data_block = reinterpret_cast<PERF_DATA_BLOCK *>(data);
    const auto *object = FindFirstObject(data_block);

    for (DWORD i = 0; i < data_block->NumObjectTypes; ++i) {
        // iterate to the object we requested since apparently there can be
        // more than that in the buffer returned
        if (object->ObjectNameTitleIndex == counter_index) {
            return object;
        }
        object = FindNextObject(object);
    }

    return nullptr;
}

std::vector<const PERF_INSTANCE_DEFINITION *> GenerateInstances(
    const PERF_OBJECT_TYPE *object) noexcept {
    if (object->NumInstances <= 0L) {
        return {};
    }

    std::vector<const PERF_INSTANCE_DEFINITION *> result;
    try {
        result.reserve(object->NumInstances);  // optimization

        const auto *instance = FirstInstance(object);
        for (auto i = 0L; i < object->NumInstances; ++i) {
            result.push_back(instance);
            instance = NextInstance(instance);
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FLINE + " exception: '{}'", e.what());
    }

    return result;
}

std::vector<std::wstring> GenerateInstanceNames(
    const PERF_OBJECT_TYPE *object) noexcept {
    if (object->NumInstances <= 0L) {
        return {};
    }

    std::vector<std::wstring> result;
    try {
        result.reserve(object->NumInstances);  // optimization
        const auto *instance = FirstInstance(object);
        for (auto i = 0L; i < object->NumInstances; ++i) {
            const auto offset =
                reinterpret_cast<const BYTE *>(instance) + instance->NameOffset;
            result.emplace_back(reinterpret_cast<LPCWSTR>(offset));

            instance = NextInstance(instance);
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FLINE + " disaster in names: '{}'", e.what());
    }
    return result;
}

// Instance less support
// DataBlock is filled when NumInstances below or equal 0
std::vector<const PERF_COUNTER_DEFINITION *> GenerateCounters(
    const PERF_OBJECT_TYPE *object,
    const PERF_COUNTER_BLOCK *&data_block) noexcept {
    std::vector<const PERF_COUNTER_DEFINITION *> result;
    data_block = nullptr;
    try {
        result.reserve(object->NumCounters);  // optimization

        const auto *counter = FirstCounter(object);
        for (DWORD i = 0UL; i < object->NumCounters; ++i) {
            result.push_back(counter);
            counter = NextCounter(counter);
        }

        // when object has no instances immediately after the counters
        // we have data block, ergo a code a bit strange
        if (object->NumInstances <= 0) {
            data_block = reinterpret_cast<const PERF_COUNTER_BLOCK *>(counter);
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FLINE + " disaster in instance less counters: '{}'",
                e.what());
    }
    return result;
}

// simplified version ignoring datablock
std::vector<const PERF_COUNTER_DEFINITION *> GenerateCounters(
    const PERF_OBJECT_TYPE *object) noexcept {
    const PERF_COUNTER_BLOCK *block = nullptr;
    return perf::GenerateCounters(object, block);
}

// used only in skype
// build map of the <id:name>
std::vector<std::wstring> GenerateCounterNames(const PERF_OBJECT_TYPE *object,
                                               const NameMap &name_map) {
    std::vector<std::wstring> result;

    const auto *counter = FirstCounter(object);
    for (DWORD i = 0UL; i < object->NumCounters; ++i) {
        auto index = counter->CounterNameTitleIndex;
        auto iter = name_map.find(index);
        if (iter != name_map.end()) {
            result.emplace_back(iter->second);
        } else {
            // use index as a name
            result.emplace_back(std::to_wstring(index));
        }

        counter = NextCounter(counter);
    }

    return result;
}

// Windows special  function to extract data
// Based on OWA => INVALID
// #TODO http://msdn.microsoft.com/en-us/library/aa373178%28v=vs.85%29.aspx
static uint64_t GetCounterValueFromBlock(
    const PERF_COUNTER_DEFINITION &counter,
    const PERF_COUNTER_BLOCK *block) noexcept {
    const unsigned offset = counter.CounterOffset;
    const auto *data = cma::tools::GetOffsetInBytes(block, offset);

    constexpr DWORD perf_size_mask = 0x00000300;

    auto *dwords = static_cast<const uint32_t *>(data);
    switch (counter.CounterType & perf_size_mask) {
        case PERF_SIZE_DWORD:
            return static_cast<uint64_t>(dwords[0]);
        case PERF_SIZE_LARGE:
            return *(UNALIGNED uint64_t *)data;  // NOLINT
        case PERF_SIZE_ZERO:
            return 0;
        default: {
            // handle other data generically. This is wrong in some
            // situation. Once upon a time in future we might implement a
            // conversion as described in
            // http://msdn.microsoft.com/en-us/library/aa373178%28v=vs.85%29.aspx
            if (counter.CounterSize == 4) {
                return static_cast<uint64_t>(dwords[0]);
            }

            if (counter.CounterSize == 8) {
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
    const PERF_COUNTER_DEFINITION &counter,
    const std::vector<const PERF_INSTANCE_DEFINITION *> &instances) noexcept {
    std::vector<uint64_t> result;
    try {
        if (!instances.empty()) {
            result.reserve(instances.size());
            for (const auto *instance : instances) {
                auto *counter_block = GetCounterBlock(instance);
                result.emplace_back(
                    GetCounterValueFromBlock(counter, counter_block));
            }
        }
    } catch (const std::exception &e) {
        XLOG::l(XLOG_FLINE + " exception: '{}'", e.what());
        return {};
    }

    return result;
}

uint64_t GetValueFromBlock(const PERF_COUNTER_DEFINITION &counter,
                           const PERF_COUNTER_BLOCK *block) noexcept {
    return block != nullptr ? GetCounterValueFromBlock(counter, block) : 0;
}

std::string GetName(uint32_t counter_type) noexcept {
    // probably we need a map here
    switch (counter_type) {
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
        default:
            return fmt::format("type({})", counter_type);
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

    auto hres = ::CoInitializeEx(nullptr, COINIT_MULTITHREADED);

    constexpr auto version_requested = MAKEWORD(2, 2);
    WSADATA wsa_data = {};
    const int err = ::WSAStartup(version_requested, &wsa_data);
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
    const auto ret = InitWindowsComSecurity();
    if (!ret) {
        XLOG::l.crit("Can't init COM SECURITY ");
        ::CoUninitialize();
        return;
    }

    XLOG::l.i("COM initialized");

    g_windows_com_initialized = true;
}

void CloseWindowsCom() {
    std::lock_guard lk(g_com_lock);
    if (!g_windows_com_initialized) return;
    ::CoUninitialize();
    XLOG::l.i("COM closed");
    g_windows_com_initialized = false;
}

bool IsWindowsComInitialized() {
    std::lock_guard lk(g_com_lock);
    return g_windows_com_initialized;
}

bool WmiObjectContains(IWbemClassObject *object, const std::wstring &name) {
    if (object == nullptr) {
        XLOG::l.crit(XLOG_FUNC + "Bad Parameter");
        return false;
    }

    VARIANT value = {};
    const HRESULT res = object->Get(name.c_str(), 0, &value, nullptr, nullptr);
    if (FAILED(res)) {
        return false;
    }

    ON_OUT_OF_SCOPE(VariantClear(&value));
    return value.vt != VT_NULL;
}

std::wstring WmiGetWstring(const VARIANT &Var) {
    if (Var.vt & VT_ARRAY) {
        return L"<array>";
    }
    if (Var.vt & VT_VECTOR) {
        return L"<vector>";
    }

    switch (Var.vt) {
        case VT_BSTR:
            return {Var.bstrVal};
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
            return std::to_wstring(Var.boolVal != 0);

        case VT_NULL:
            return L"";

        default:
            XLOG::l.crit("Unknown data type in Vector [{}]", Var.vt);
            return L"";
    }
}

std::wstring WmiStringFromObject(IWbemClassObject *object,
                                 const std::vector<std::wstring> &names,
                                 std::wstring_view separator) {
    std::wstring result;
    for (const auto &name : names) {
        VARIANT value = {};
        memset(&value, 0, sizeof value);
        // Get the value of the Name property
        auto hres = object->Get(name.c_str(), 0, &value, nullptr, nullptr);
        if (SUCCEEDED(hres)) {
            ON_OUT_OF_SCOPE(VariantClear(&value));
            auto str = wtools::WmiGetWstring(value);
            if (str[0] == '-') {
                XLOG::t("WMI Negative value '{}' [{}], type [{}]", ToUtf8(name),
                        ToUtf8(str), value.vt);
            }
            result += str;
        } else {
            XLOG::t("Missing value for name '{}' error {:#X}",
                    wtools::ToUtf8(name), hres);
        }
        result += separator;
    }
    if (result.empty()) {
        XLOG::d("We have empty result for wbm_object, this is unusual");
        return {};
    }

    result.pop_back();  // remove last L","
    return result;
}

std::wstring WmiStringFromObject(IWbemClassObject *object,
                                 const std::wstring &name) {
    VARIANT value = {};
    if (FAILED(object->Get(name.c_str(), 0, &value, nullptr, nullptr))) {
        return {};
    }

    ON_OUT_OF_SCOPE(VariantClear(&value));
    return wtools::WmiGetWstring(value);
}

std::optional<std::wstring> WmiTryGetString(IWbemClassObject *object,
                                            const std::wstring &name) {
    VARIANT value = {};
    if (FAILED(object->Get(name.c_str(), 0, &value, nullptr, nullptr))) {
        return {};
    }

    ON_OUT_OF_SCOPE(VariantClear(&value));
    if (value.vt == VT_NULL) {
        return {};
    }
    return wtools::WmiGetWstring(value);
}

uint64_t WmiUint64FromObject(IWbemClassObject *object,
                             const std::wstring &name) {
    VARIANT value = {};
    if (FAILED(object->Get(name.c_str(), 0, &value, nullptr, nullptr))) {
        return 0;
    }

    ON_OUT_OF_SCOPE(VariantClear(&value));
    if (value.vt == VT_NULL) {
        return {};
    }
    return wtools::WmiGetUint64(value);
}

/// returns name vector
/// on error returns empty
std::vector<std::wstring> WmiGetNamesFromObject(IWbemClassObject *wmi_object) {
    SAFEARRAY *names = nullptr;
    HRESULT res = wmi_object->GetNames(
        nullptr, WBEM_FLAG_ALWAYS | WBEM_FLAG_NONSYSTEM_ONLY, nullptr, &names);
    if (FAILED(res) || nullptr == names) {
        XLOG::l.e("Failed to get names from wmi_object {:#X}", res);
        return {};  // Program has failed.
    }
    ON_OUT_OF_SCOPE(if (names) { ::SafeArrayDestroy(names); });

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
    result.reserve(static_cast<size_t>(end - start) + 1);

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

        result.emplace_back(property_name);
    }

    return result;
}

// returns valid enumerator or nullptr
IEnumWbemClassObject *WmiExecQuery(IWbemServices *services,
                                   const std::wstring &query) noexcept {
    XLOG::t("query is '{}'", ToUtf8(query));
    IEnumWbemClassObject *enumerator = nullptr;
    auto hres = services->ExecQuery(
        bstr_t("WQL"),          // always the same
        bstr_t(query.c_str()),  // text of query
        WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY,  // legacy agent
        nullptr,                                                // nobody knows
        &enumerator);

    if (SUCCEEDED(hres)) {
        return enumerator;
    }
    // SHOULD NOT HAPPEN
    XLOG::l.e("Failed query wmi {:#X}, query is {}",
              static_cast<unsigned>(hres), ToUtf8(query));
    return nullptr;
}

bool WmiWrapper::open() noexcept {
    std::lock_guard lk(lock_);
    IWbemLocator *locator = nullptr;

    auto hres = ::CoCreateInstance(CLSID_WbemLocator, nullptr,
                                   CLSCTX_INPROC_SERVER, IID_IWbemLocator,
                                   reinterpret_cast<void **>(&locator));

    if (FAILED(hres)) {
        XLOG::l.crit("Can't Create Instance WMI {:#X}",
                     static_cast<unsigned long>(hres));
        return false;
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
bool WmiWrapper::connect(std::wstring_view name_space) noexcept {
    if (name_space.empty()) {
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
        locator_->ConnectServer(_bstr_t(name_space.data()),  // WMI namespace
                                nullptr,                     // User name
                                nullptr,                     // User password
                                nullptr,                     // Locale
                                0,                           // Security flags
                                nullptr,                     // Authority
                                nullptr,                     // Context object
                                &services_  // IWbemServices proxy
        );

    if (SUCCEEDED(hres)) {
        return true;
    }

    XLOG::l.e("Can't connect to the namespace {} {:#X}", ToUtf8(name_space),
              static_cast<unsigned long>(hres));
    return false;  // Program has failed.
}

// This is OPTIONAL feature, LWA doesn't use it
bool WmiWrapper::impersonate() const noexcept {
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

    if (SUCCEEDED(hres)) {
        return true;
    }

    XLOG::l.e("Failed blanker/impersonation locator wmI {:X}", hres);
    return false;  // Program has failed.
}

// RETURNS RAW OBJECT
// returns nullptr, WmiStatus
std::tuple<IWbemClassObject *, WmiStatus> WmiGetNextObject(
    IEnumWbemClassObject *enumerator, uint32_t timeout) {
    if (enumerator == nullptr) {
        XLOG::l.e("nullptr in Enumerator");
        return {nullptr, WmiStatus::error};
    }
    ULONG returned{0};
    IWbemClassObject *wmi_object{nullptr};

    auto hres = enumerator->Next(static_cast<long>(timeout) * 1000, 1,
                                 &wmi_object, &returned);
    switch (hres) {
        case WBEM_S_TIMEDOUT:
            XLOG::l.e("Timeout [{}] seconds broken  when query WMI", timeout);
            return {nullptr, WmiStatus::timeout};
        case WBEM_S_FALSE:
            return {nullptr, WmiStatus::ok};  // no more data
        case WBEM_NO_ERROR:
            return returned == 0 ? std::tuple{nullptr, WmiStatus::ok}  // eof
                                 : std::tuple{wmi_object, WmiStatus::ok};
        default:
            XLOG::t("Return {:#X}. Object doesn't exist",
                    static_cast<uint64_t>(hres));
            return {nullptr, WmiStatus::error};
    }
}

static void FillAccuAndNames(std::wstring &accu,
                             std::vector<std::wstring> &names,
                             IWbemClassObject *wmi_object,
                             std::wstring_view separator) {
    if (names.empty()) {
        // we have asking for everything, ergo we have to use
        // get name list from WMI
        names = wtools::WmiGetNamesFromObject(wmi_object);
    }
    accu = cma::tools::JoinVector(names, separator);
    if (accu.empty()) {
        XLOG::l("Failed to get names");
    } else {
        accu += L'\n';
    }
}

// returns nullptr, WmiStatus
std::tuple<std::wstring, WmiStatus> WmiWrapper::produceTable(
    IEnumWbemClassObject *enumerator,
    const std::vector<std::wstring> &existing_names,
    std::wstring_view separator, uint32_t wmi_timeout) noexcept {
    // preparation
    std::wstring accu;
    auto status_to_return = WmiStatus::ok;

    bool accu_is_empty = true;
    // setup default names vector
    auto names = existing_names;

    // processing loop
    while (nullptr != enumerator) {
        auto [wmi_object, status] = WmiGetNextObject(enumerator, wmi_timeout);
        status_to_return = status;  // last status is most important

        if (nullptr == wmi_object) {
            break;
        }

        auto kill_wmi_object = wmi_object;
        ON_OUT_OF_SCOPE(kill_wmi_object->Release());

        // init accu with names
        if (accu_is_empty) {
            FillAccuAndNames(accu, names, wmi_object, separator);
            accu_is_empty = false;
        }

        auto raw = wtools::WmiStringFromObject(wmi_object, names, separator);
        if (!raw.empty()) {
            accu += raw + L"\n";
        }
    }

    return {accu, status_to_return};
}

std::wstring WmiWrapper::makeQuery(const std::vector<std::wstring> &names,
                                   const std::wstring &target) noexcept {
    auto name_list = cma::tools::JoinVector(names, L",");

    if (name_list.empty()) {
        name_list = L"*";
    }
    std::wstring query_text = L"SELECT " + name_list + L" FROM " + target;
    return query_text;
}

// work horse to ask certain names from the target
// returns "", Status
std::tuple<std::wstring, WmiStatus> WmiWrapper::queryTable(
    const std::vector<std::wstring> &names, const std::wstring &target,
    std::wstring_view separator, uint32_t wmi_timeout) const noexcept {
    auto query_text = makeQuery(names, target);

    // Send a query to system
    std::lock_guard lk(lock_);
    auto *enumerator = wtools::WmiExecQuery(services_, query_text);

    // make a table using enumerator and supplied Names vector
    if (nullptr == enumerator) {
        XLOG::d("WMI enumerator is null for '{}'", ToUtf8(target));
        return {std::wstring(), WmiStatus::error};
    }
    ON_OUT_OF_SCOPE(enumerator->Release());

    return produceTable(enumerator, names, separator, wmi_timeout);
}

// special purposes: formatting for PS for example
// on error returns nullptr
IEnumWbemClassObject *WmiWrapper::queryEnumerator(
    const std::vector<std::wstring> &names,
    const std::wstring &target) const noexcept {
    auto query_text = makeQuery(names, target);

    // Send a query to system
    std::lock_guard lk(lock_);
    return wtools::WmiExecQuery(services_, query_text);
}

HMODULE LoadWindowsLibrary(const std::wstring &dll_path) {
    // this should be sufficient most of the time
    constexpr size_t buffer_size = 512;

    std::wstring dllpath_expanded;
    dllpath_expanded.resize(buffer_size, '\0');
    DWORD required =
        ExpandEnvironmentStringsW(dll_path.c_str(), dllpath_expanded.data(),
                                  static_cast<DWORD>(dllpath_expanded.size()));

    if (required > dllpath_expanded.size()) {
        dllpath_expanded.resize(required + 1);
        required = ExpandEnvironmentStringsW(
            dll_path.c_str(), dllpath_expanded.data(),
            static_cast<DWORD>(dllpath_expanded.size()));
    } else if (required == 0) {
        dllpath_expanded = dll_path;
    }
    if (required != 0) {
        // required includes the zero terminator
        dllpath_expanded.resize(required - 1);
    }

    // load the library as a datafile without loading referenced dlls. This
    // is quicker but most of all it prevents problems if dependent dlls
    // can't be loaded.
    return ::LoadLibraryExW(
        dllpath_expanded.c_str(), nullptr,
        DONT_RESOLVE_DLL_REFERENCES | LOAD_LIBRARY_AS_DATAFILE);
}

/// Look into the registry in order to find out, which event logs are available
std::vector<std::string> EnumerateAllRegistryKeys(const char *reg_path) {
    HKEY key = nullptr;
    auto r =
        ::RegOpenKeyExW(HKEY_LOCAL_MACHINE, ConvertToUtf16(reg_path).c_str(), 0,
                        KEY_ENUMERATE_SUB_KEYS, &key);  // NOLINT
    if (r != ERROR_SUCCESS) {
        XLOG::l(" Cannot open registry key '{}' error [{}]", reg_path,
                ::GetLastError());
        return {};
    }
    ON_OUT_OF_SCOPE(::RegCloseKey(key));

    std::vector<std::string> entries;
    constexpr int buf_len = 1024;
    for (DWORD i = 0; r == ERROR_SUCCESS || r == ERROR_MORE_DATA; ++i) {
        wchar_t key_name[buf_len];
        DWORD len = buf_len;
        r = ::RegEnumKeyExW(key, i, key_name, &len, nullptr, nullptr, nullptr,
                            nullptr);
        if (r == ERROR_NO_MORE_ITEMS) {
            break;
        }

        if (r != ERROR_SUCCESS) {
            XLOG::l("Failed to enum '{}' error [{}]", ToUtf8(key_name), r);
            break;
        }
        entries.emplace_back(ToUtf8(key_name));
    }
    return entries;
}

uint32_t GetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                          uint32_t dflt) noexcept {
    HKEY hkey = nullptr;
    auto ret = ::RegOpenKeyW(HKEY_LOCAL_MACHINE, path.data(), &hkey);  // NOLINT
    if (ret == ERROR_SUCCESS && hkey != nullptr) {
        ON_OUT_OF_SCOPE(::RegCloseKey(hkey));
        DWORD type = REG_DWORD;
        uint32_t buffer = dflt;
        DWORD count = sizeof buffer;
        ret = ::RegQueryValueExW(hkey, value_name.data(), nullptr, &type,
                                 reinterpret_cast<LPBYTE>(&buffer), &count);
        if (ret == ERROR_SUCCESS && 0 != count && type == REG_DWORD) {
            return buffer;
        }
    }
    XLOG::t(XLOG_FLINE + "Absent {}\\{} query [{}]", ToUtf8(path),
            ToUtf8(value_name), ret);
    return dflt;
}

bool DeleteRegistryValue(std::wstring_view path,
                         std::wstring_view value_name) noexcept {
    HKEY hkey = nullptr;
    auto ret = ::RegOpenKeyW(HKEY_LOCAL_MACHINE, path.data(), &hkey);
    if (ERROR_SUCCESS == ret && nullptr != hkey) {
        ON_OUT_OF_SCOPE(::RegCloseKey(hkey));
        ret = ::RegDeleteValue(hkey, value_name.data());
        if (ret == ERROR_SUCCESS) {
            return true;
        }
        if (ret == ERROR_FILE_NOT_FOUND) {
            XLOG::t.t(XLOG_FLINE + "No need to delete {}\\{}", ToUtf8(path),
                      ToUtf8(value_name));
            return true;
        }

        XLOG::l(XLOG_FLINE + "Failed to delete {}\\{} error [{}]", ToUtf8(path),
                ToUtf8(value_name), ret);
        return false;
    }
    //  here
    XLOG::t.t(XLOG_FLINE + "No need to delete {}\\{}", ToUtf8(path),
              ToUtf8(value_name));
    return true;
}

namespace {

HKEY CreateRegistryKey(std::wstring_view path) noexcept {
    HKEY key = nullptr;
    return ::RegCreateKeyEx(HKEY_LOCAL_MACHINE, path.data(), 0L, nullptr,
                            REG_OPTION_NON_VOLATILE, KEY_ALL_ACCESS, nullptr,
                            &key, nullptr) == ERROR_SUCCESS
               ? key
               : nullptr;  // NOLINT
}
// returns true on success
bool SetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                      std::wstring_view value, DWORD type) noexcept {
    auto *key = CreateRegistryKey(path);
    if (key == nullptr) {
        return false;
    }

    // Set full application path with a keyname to registry
    auto ret =
        ::RegSetValueEx(key, value_name.data(), 0, type,
                        reinterpret_cast<const BYTE *>(value.data()),
                        static_cast<uint32_t>(value.size() * sizeof(wchar_t)));
    ::RegCloseKey(key);
    return ERROR_SUCCESS == ret;
}
}  // namespace

bool SetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                      std::wstring_view value) noexcept {
    return SetRegistryValue(path, value_name, value, REG_SZ);
}

bool SetRegistryValueExpand(std::wstring_view path,
                            std::wstring_view value_name,
                            std::wstring_view value) {
    return SetRegistryValue(path, value_name, value, REG_EXPAND_SZ);
}

// returns true on success
bool SetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                      uint32_t value) noexcept {
    auto ret =
        ::RegSetKeyValue(HKEY_LOCAL_MACHINE, path.data(), value_name.data(),
                         REG_DWORD, &value, 4);  // NOLINT
    if (ret != ERROR_SUCCESS) {
        XLOG::d("Bad with reg set value {}", ret);
    }

    return ret == ERROR_SUCCESS;
}

std::wstring GetRegistryValue(std::wstring_view path,
                              std::wstring_view value_name,
                              std::wstring_view dflt) noexcept {
    HKEY hkey = nullptr;
    if (dflt.data() == nullptr) {
        dflt = L"";
    }
    auto result =
        ::RegOpenKeyW(HKEY_LOCAL_MACHINE, path.data(), &hkey);  // NOLINT
    if (result != ERROR_SUCCESS || hkey == nullptr) {
        // failure here
        XLOG::t.t(XLOG_FLINE + "Cannot open Key '{}' query return code [{}]",
                  ToUtf8(path), result);
        return dflt.data();
    }

    ON_OUT_OF_SCOPE(::RegCloseKey(hkey));
    DWORD type = REG_SZ;
    wchar_t buffer[512] = {0};
    DWORD count = sizeof buffer;
    auto ret = ::RegQueryValueExW(hkey, value_name.data(), nullptr, &type,
                                  reinterpret_cast<LPBYTE>(buffer), &count);

    // check for errors
    auto type_ok = type == REG_SZ || type == REG_EXPAND_SZ;
    if (count == 0 || !type_ok) {
        // failure here
        XLOG::t.t(XLOG_FLINE + "Can't open '{}\\{}' query returns [{}]",
                  ToUtf8(path), ToUtf8(value_name), ret);
        return dflt.data();
    }

    if (ret == ERROR_SUCCESS) {
        return type == REG_SZ ? buffer : ExpandStringWithEnvironment(buffer);
    }

    if (ret == ERROR_MORE_DATA) {
        // realloc required
        type = REG_SZ;
        auto *buffer_big = new wchar_t[count / sizeof(wchar_t) + 2];
        ON_OUT_OF_SCOPE(delete[] buffer_big);
        count = sizeof count;
        ret = ::RegQueryValueExW(hkey, value_name.data(), nullptr, &type,
                                 reinterpret_cast<LPBYTE>(buffer_big), &count);

        // check for errors
        type_ok = type == REG_SZ || type == REG_EXPAND_SZ;
        if (count == 0 || !type_ok) {
            // failure here
            XLOG::t.t(XLOG_FLINE + "Absent {}\\{} query return [{}]",
                      ToUtf8(path), ToUtf8(value_name), ret);
            return dflt.data();
        }

        if (ret == ERROR_SUCCESS) {
            return type == REG_SZ ? buffer_big
                                  : ExpandStringWithEnvironment(buffer_big);
        }
    }

    // failure here
    XLOG::t.t(XLOG_FLINE + "Bad key {}\\{} query return [{}]", ToUtf8(path),
              ToUtf8(value_name), ret);
    return dflt.data();
}

// process terminators
bool KillProcess(uint32_t pid, int exit_code) noexcept {
    auto *handle = ::OpenProcess(PROCESS_TERMINATE, FALSE, pid);
    if (handle == nullptr) {
        if (::GetLastError() == 5) {
            XLOG::d("Can't open process for termination ACCESS is DENIED [{}]",
                    pid);
        }
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseHandle(handle));

    if (::TerminateProcess(handle, exit_code) == FALSE) {
        // - we have no problem(process already dead) - ignore
        // - we have problem: either exit_code is invalid or something wrong
        // with Windows in all cases just report
        XLOG::d("Cannot terminate process [{}] gracefully, error [{}]", pid,
                ::GetLastError());
        return false;
    }

    return true;
}

// process terminator
// used to kill OpenHardwareMonitor or Agent controller
bool KillProcess(std::wstring_view process_name, int exit_code) noexcept {
    auto *snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPALL, NULL);
    if (snapshot == nullptr) {
        return false;
    }

    const auto current_process_id = GetCurrentProcessId();

    ON_OUT_OF_SCOPE(CloseHandle(snapshot));

    PROCESSENTRY32 entry32 = {};
    entry32.dwSize = sizeof entry32;
    auto result = Process32First(snapshot, &entry32);
    while (result != 0) {
        if (cma::tools::IsEqual(std::wstring_view(entry32.szExeFile),
                                process_name) &&
            entry32.th32ProcessID != current_process_id) {
            auto *process =
                ::OpenProcess(PROCESS_TERMINATE, 0, entry32.th32ProcessID);
            if (process != nullptr) {
                ::TerminateProcess(process, exit_code);
                ::CloseHandle(process);
            }
        }
        result = ::Process32Next(snapshot, &entry32);
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
std::string WmiPostProcess(const std::string &in, StatusColumn status_column,
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
                   [&tail_for_data](const std::string &value) {
                       return value + tail_for_data;
                   });

    return std::accumulate(table.begin(), table.end(), std::string());
}

/// returns false on system failure
// based on ToolHelp api family
// normally require elevation
// if action returns false, scan will be stopped(this is only optimization)
bool ScanProcessList(
    const std::function<ScanAction(const PROCESSENTRY32 &)> &action) {
    auto *snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPALL, NULL);
    if (snapshot == nullptr) {
        return false;
    }

    ON_OUT_OF_SCOPE(::CloseHandle(snapshot));

    const auto current_process_id = ::GetCurrentProcessId();
    PROCESSENTRY32 entry32 = {};
    entry32.dwSize = sizeof entry32;
    auto result = ::Process32First(snapshot, &entry32);
    while (result != FALSE) {
        if (entry32.th32ProcessID == current_process_id ||
            action(entry32) == ScanAction::advance) {
            result = ::Process32Next(snapshot, &entry32);
        } else {
            return true;
        }
    }

    return true;
}

// finds all process and kills them with all their children
bool KillProcessFully(const std::wstring &process_name,
                      int exit_code) noexcept {
    std::vector<DWORD> processes_to_kill;
    std::wstring name{process_name};
    cma::tools::WideLower(name);
    ScanProcessList([&processes_to_kill, name](const PROCESSENTRY32 &entry) {
        std::wstring incoming_name = entry.szExeFile;
        cma::tools::WideLower(incoming_name);
        if (name == incoming_name)
            processes_to_kill.push_back(entry.th32ProcessID);
        return ScanAction::advance;
    });

    for (auto proc_id : processes_to_kill) {
        KillProcessTree(proc_id);
        KillProcess(proc_id, exit_code);
    }

    return true;
}

// finds all process and kills them with all their children
int FindProcess(std::wstring_view process_name) noexcept {
    int count = 0;
    std::wstring name(process_name);
    cma::tools::WideLower(name);
    ScanProcessList([name, &count](const PROCESSENTRY32 &entry) {
        std::wstring incoming_name = entry.szExeFile;
        cma::tools::WideLower(incoming_name);
        if (name == incoming_name) {
            count++;
        }
        return ScanAction::advance;
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
    ZeroMemory(&process, sizeof process);
    process.dwSize = sizeof process;
    Process32First(snapshot, &process);
    do {
        // process.th32ProcessId is the PID.
        if (process.th32ParentProcessID == ProcessId) {
            KillProcess(process.th32ProcessID, 99);
        }

    } while (Process32Next(snapshot, &process));
}

std::wstring GetArgv(uint32_t index) noexcept {
    int n_args = 0;
    auto *argv = ::CommandLineToArgvW(GetCommandLineW(), &n_args);

    if (argv == nullptr) {
        return {};
    }

    ON_OUT_OF_SCOPE(::LocalFree(argv));

    if (index < static_cast<uint32_t>(n_args)) {
        return argv[index];
    }

    return {};
}

fs::path GetCurrentExePath() {
    if (WCHAR path[MAX_PATH]; ::GetModuleFileNameW(nullptr, path, MAX_PATH)) {
        return {path};
    }
    XLOG::l("Can't determine exe path [{}]", ::GetLastError());
    return {};
}

namespace {
std::optional<PROCESS_MEMORY_COUNTERS_EX> GetProcessMemoryCounters(
    HANDLE process) {
    PROCESS_MEMORY_COUNTERS_EX counters = {};
    counters.cb = sizeof counters;
    if (::GetProcessMemoryInfo(process,
                               static_cast<PROCESS_MEMORY_COUNTERS *>(
                                   static_cast<void *>(&counters)),
                               counters.cb) == 0) {
        XLOG::l("Can't read process memory, error [{}]", ::GetLastError());
        return {};
    }
    return counters;
}
}  // namespace

/// See:
/// https://en.wikipedia.org/wiki/Commit_charge
/// commit charge may be defined as 'virtual memory size', i.e. size of process
/// which backed up by physical memory and/or pagefile
/// https://docs.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex
/// PrivateUsage(PageFileUsage for newer OS) means Commit Charge
size_t GetCommitCharge(uint32_t pid) noexcept {
    UniqueHandle h{
        ::OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid)};

    if (!h) {
        XLOG::t.i("Can't open process with pid [{}], error [{}]", pid,
                  ::GetLastError());
        return 0;
    }

    auto counters = GetProcessMemoryCounters(h.get());
    return counters ? counters->PrivateUsage : 0;
}

size_t GetOwnVirtualSize() noexcept {
    auto counters = GetProcessMemoryCounters(GetCurrentProcess());
    return counters ? counters->WorkingSetSize : 0;
}

namespace monitor {
bool IsAgentHealthy() noexcept {
    return GetOwnVirtualSize() < kMaxMemoryAllowed;
}
}  // namespace monitor

// Low level function to get parent reliable
uint32_t GetParentPid(uint32_t pid)  // By Napalm @ NetCore2K
{
    ULONG_PTR pbi[6] = {0};
    ULONG size = 0;
    LONG(WINAPI * nt_query_information_process)(
        HANDLE ProcessHandle, ULONG ProcessInformationClass,
        PVOID ProcessInformation, ULONG ProcessInformationLength,
        PULONG ReturnLength) = nullptr;
    *(FARPROC *)&nt_query_information_process = ::GetProcAddress(
        LoadLibraryA("NTDLL.DLL"), "NtQueryInformationProcess");  // NOLINT
    if (nt_query_information_process == nullptr) {
        return 0;
    }

    const HANDLE h = ::OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, pid);
    if (h == nullptr) {
        XLOG::l.w("Can't get info from process [{}] error [{}]", pid,
                  GetLastError());

        return 0;
    }
    ON_OUT_OF_SCOPE(CloseHandle(h));

    if (nt_query_information_process(h, 0, &pbi, sizeof pbi, &size) >= 0 &&
        size == sizeof pbi)
        return static_cast<uint32_t>(pbi[5]);

    return 0;
}

#define READ_PERMISSIONS (FILE_READ_DATA | FILE_READ_ATTRIBUTES)  // NOLINT
#define WRITE_PERMISSIONS                                         \
    (FILE_WRITE_DATA | FILE_APPEND_DATA | FILE_WRITE_ATTRIBUTES | \
     FILE_WRITE_EA)  // NOLINT

#define EXECUTE_PERMISSIONS (FILE_READ_DATA | FILE_EXECUTE)  // NOLINT

// Constructor
ACLInfo::ACLInfo(const _bstr_t &bstrPath) noexcept {
    ace_list_ = nullptr;
    path_ = bstrPath;
}

// Destructor
ACLInfo::~ACLInfo() {
    // Free ace_list structure
    clearAceList();
}

// Free the nodes of ace_list
void ACLInfo::clearAceList() noexcept {
    AceList *ace_list = ace_list_;
    AceList *next = nullptr;
    while (nullptr != ace_list) {
        next = ace_list->next;
        free(ace_list);  // NOLINT
        ace_list = next;
    }

    ace_list_ = nullptr;
}

HRESULT ACLInfo::query() noexcept {
    DWORD size_needed = 0;

    // clear any previously queried information
    clearAceList();

    // Find out size of needed buffer for security descriptor with DACL
    // DACL = Discretionary Access Control List
    ::GetFileSecurityW(path_.GetBSTR(), DACL_SECURITY_INFORMATION, nullptr, 0,
                       &size_needed);

    if (size_needed == 0) {
        return E_FAIL;
    }
    const auto security_descriptor_buffer = new BYTE[size_needed];

    // Retrieve security descriptor with DACL information
    auto success = ::GetFileSecurityW(
        path_.GetBSTR(), DACL_SECURITY_INFORMATION, security_descriptor_buffer,
        size_needed, &size_needed);

    // Check if we successfully retrieved security descriptor with DACL
    // information
    if (success == FALSE) {
        XLOG::l("Failed to get file security information {}", ::GetLastError());
        return E_FAIL;
    }

    // Getting DACL from Security Descriptor
    PACL acl = nullptr;
    BOOL dacl_present = FALSE;
    BOOL dacl_defaulted = FALSE;
    success = ::GetSecurityDescriptorDacl(
        reinterpret_cast<SECURITY_DESCRIPTOR *>(security_descriptor_buffer),
        &dacl_present, &acl, &dacl_defaulted);

    // Check if we successfully retrieved DACL
    if (success == FALSE) {
        XLOG::l("Failed to retrieve DACL from security descriptor {}",
                ::GetLastError());
        return E_FAIL;
    }

    // Check if DACL present in security descriptor
    if (dacl_present == FALSE) {
        XLOG::l("DACL was not found.");
        return E_FAIL;
    }

    // DACL for specified file was retrieved successfully
    // Now, we should fill in the linked list of ACEs
    // Iterate through ACEs (Access Control Entries) of DACL
    for (USHORT i = 0; i < acl->AceCount; i++) {
        void *ace = nullptr;
        success = ::GetAce(acl, i, &ace);
        if (success == FALSE) {
            DWORD error = ::GetLastError();
            XLOG::l("Failed to get ace {}, {}", i, error);
            continue;
        }
        HRESULT hr = addAceToList(static_cast<ACE_HEADER *>(ace));
        if (FAILED(hr)) {
            XLOG::l("Failed to add ace {} to list", i);
        }
    }
    return S_OK;
}

HRESULT ACLInfo::addAceToList(ACE_HEADER *ace) noexcept {
    auto *new_ace = static_cast<AceList *>(malloc(sizeof AceList));
    if (new_ace == nullptr) {
        return S_FALSE;
    }
    switch (ace->AceType) {
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
    new_ace->ace = ace;
    new_ace->next = ace_list_;

    ace_list_ = new_ace;

    return S_OK;
}

namespace {
std::string PrintPermissions(bool allowed, ACCESS_MASK permissions) {
    constexpr std::array mapping = {std::pair{READ_PERMISSIONS, "R"},
                                    std::pair{WRITE_PERMISSIONS, "W"},
                                    std::pair{EXECUTE_PERMISSIONS, "X"}};
    std::string os;
    if (allowed) {
        for (const auto &[value, text] : mapping) {
            os += (value & permissions) == value ? text : " ";
        }
    } else {
        for (const auto &[value, text] : mapping) {
            os += (value & permissions) != 0 ? text : " ";
        }
    }
    return os;
}

std::string MakeReadableString(bool allowed, std::string_view domain,
                               std::string_view name, ACCESS_MASK permissions) {
    std::string os;
    // Output Account info (in NT4 style: domain\user)
    os += allowed ? "Allowed to: " : "Denied from: ";

    if (!domain.empty()) {
        os += domain;
        os += "\\";
    }
    os += name;
    os += " [";
    os += PrintPermissions(allowed, permissions);
    os += "]";
    return os;
}

SID *ExtractSid(const ACLInfo::AceList *list) {
    auto *ace = list->ace;
    auto *sid_start =
        list->allowed ? &reinterpret_cast<ACCESS_ALLOWED_ACE *>(ace)->SidStart
                      : &reinterpret_cast<ACCESS_DENIED_ACE *>(ace)->SidStart;

    return reinterpret_cast<SID *>(sid_start);
}

ACCESS_MASK ExtractPermissions(const ACLInfo::AceList *list) {
    const auto *ace = list->ace;
    return list->allowed
               ? reinterpret_cast<const ACCESS_ALLOWED_ACE *>(ace)->Mask
               : reinterpret_cast<const ACCESS_DENIED_ACE *>(ace)->Mask;
}
std::pair<std::string, std::string> GetAccountName(SID *sid) {
    SID_NAME_USE sid_name_use{SidTypeUser};
    char name_buffer[MAX_PATH];
    char domain_buffer[MAX_PATH];
    DWORD name_len = sizeof name_buffer;
    DWORD domain_name_len = sizeof domain_buffer;

    // Get account name for SID
    if (::LookupAccountSidA(nullptr, sid, name_buffer, &name_len, domain_buffer,
                            &domain_name_len, &sid_name_use) == FALSE) {
        XLOG::l("Failed to get account for SID, error = [{}]",
                ::GetLastError());
        return {{}, {}};
    }
    return {domain_buffer, name_buffer};
}
}  // namespace

std::string ACLInfo::output() const {
    if (ace_list_ == nullptr) {
        return "No ACL Info\n";
    }
    auto *list = ace_list_;
    std::string os;
    while (list != nullptr) {
        const auto [domain, name] = GetAccountName(ExtractSid(list));
        if (name.empty()) {
            continue;
        }
        os += MakeReadableString(list->allowed == TRUE, domain, name,
                                 ExtractPermissions(list));
        os += "\n";
        list = list->next;
    }
    return os;
}

std::string ReadWholeFile(const fs::path &fname) noexcept {
    try {
        std::ifstream f(ToUtf8(fname.wstring()), std::ios::binary);

        if (!f.good()) {
            return {};
        }

        f.seekg(0, std::ios::end);
        auto fsize = static_cast<uint32_t>(f.tellg());

        // read contents
        f.seekg(0, std::ios::beg);
        std::string v;
        v.resize(fsize);
        f.read(v.data(), fsize);
        return v;
    } catch (const std::exception &e) {
        // catching possible exceptions in the
        // ifstream or memory allocations
        XLOG::l(XLOG_FUNC + "Exception '{}' generated in read file", e.what());
        return {};
    }
}

bool PatchFileLineEnding(const fs::path &fname) noexcept {
    auto result = ReadWholeFile(fname);
    if (result.empty()) {
        return false;
    }

    try {
        std::ofstream tst(ToUtf8(fname.wstring()));  // text file
        tst.write(result.c_str(), static_cast<std::streamsize>(result.size()));
        return true;
    } catch (const std::exception &e) {
        XLOG::l("Error during patching file line ending {}", e.what());
        return false;
    }
}

std::wstring GenerateRandomString(size_t max_length) noexcept {
    std::wstring possible_characters(
        L"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_#@$^&()[]{};:");

    std::random_device rd;
    std::mt19937 generator(rd());

    std::uniform_int_distribution dist(
        0, static_cast<int>(possible_characters.size()) - 1);
    std::wstring ret;
    for (size_t i = 0; i < max_length; i++) {
        const int random_index =
            dist(generator);  // get index between 0 and
                              // possible_characters.size()-1
        ret += possible_characters[random_index];
    }

    return ret;
}

namespace {
std::wstring CmaUserPrefix() noexcept {
    switch (cma::GetModus()) {
        case cma::Modus::service:
            return L"cmk_in_";
        case cma::Modus::test:
            return L"cmk_TST_";
        case cma::Modus::integration:
            return L"cmk_IT_";
        case cma::Modus::app:
            return {};
    }
    // unreachable
    return {};
}
}  // namespace

std::wstring GenerateCmaUserNameInGroup(std::wstring_view group,
                                        std::wstring_view prefix) noexcept {
    if (group.empty()) {
        return {};
    }

    auto group_name = std::wstring{group};
    rs::replace(group_name, ' ', '_');
    auto name =
        prefix.empty() ? std::wstring{} : std::wstring{prefix} + group_name;
    // sometimes some Windows may restrict user name length
    if (name.size() > 20) {
        XLOG::l("User name '{}' is too long", ToUtf8(name));
        name = name.substr(0, 20);
    }
    return name;
}

std::wstring GenerateCmaUserNameInGroup(std::wstring_view group) noexcept {
    return GenerateCmaUserNameInGroup(group, CmaUserPrefix());
}

InternalUser CreateCmaUserInGroup(const std::wstring &group_name) noexcept {
    return CreateCmaUserInGroup(group_name, CmaUserPrefix());
}

InternalUser CreateCmaUserInGroup(const std::wstring &group_name,
                                  std::wstring_view prefix) noexcept {
    auto name = GenerateCmaUserNameInGroup(group_name, prefix);
    if (name.empty()) {
        XLOG::l("Failed to create user name");
        return {};
    }

    auto pwd = GenerateRandomString(12);

    const uc::LdapControl primary_dc;
    const auto add_user_status = primary_dc.userAdd(name, pwd);
    switch (add_user_status) {
        case uc::Status::success:
            break;
        case uc::Status::exists:
            XLOG::d.i("User '{}' already exists, updating credentials",
                      ToUtf8(name));
            if (primary_dc.changeUserPassword(name, pwd) !=
                uc::Status::success) {
                XLOG::l("Failed to change password for user '{}'",
                        ToUtf8(name));
                return {};
            }
            return {name, pwd};
        case uc::Status::error:
        case uc::Status::no_domain_service:
        case uc::Status::absent:
            XLOG::l("Can't add user '{}' status = {}", ToUtf8(name),
                    static_cast<int>(add_user_status));
            return {};
    }

    if (primary_dc.localGroupAddMembers(group_name, name) ==
        uc::Status::error) {
        XLOG::l("Can't add user '{}' to group_name '{}'", ToUtf8(name),
                ToUtf8(group_name));
        if (add_user_status == uc::Status::success) {
            const auto del_ret = primary_dc.userDel(name);
            XLOG::t("recover delete state {}", static_cast<int>(del_ret));
        }

        return {};
    }
    return {name, pwd};
}

bool RemoveCmaUser(const std::wstring &user_name) noexcept {
    const uc::LdapControl primary_dc;
    return primary_dc.userDel(user_name) != uc::Status::error;
}

void ProtectPathFromUserWrite(const fs::path &path,
                              std::vector<std::wstring> &commands) {
    // CONTEXT: to prevent malicious file creation or modification  in folder
    // "programdata/checkmk" we must remove inherited write rights for
    // Users in checkmk root data folder.

    // disable inheritance
    commands.emplace_back(
        fmt::format(L"icacls \"{}\" /inheritance:d /c", path.wstring()));
    // remove all user rights
    commands.emplace_back(fmt::format(
        L"icacls \"{}\" /remove:g *S-1-5-32-545 /c", path.wstring()));
    // read/exec
    commands.emplace_back(
        fmt::format(L"icacls \"{}\" /grant:r *S-1-5-32-545:(OI)(CI)(RX) /c",
                    path.wstring()));

    XLOG::l.i("Protect path from User write '{}'", path);
}

void ProtectFileFromUserWrite(const fs::path &path,
                              std::vector<std::wstring> &commands) {
    // CONTEXT: to prevent malicious file creation or modification  in
    // folder "programdata/checkmk" we must remove inherited write rights
    // for Users in checkmk root data folder.

    // disable inheritance
    commands.emplace_back(
        fmt::format(L"icacls \"{}\" /inheritance:d /c", path.wstring()));
    // remove all user rights
    commands.emplace_back(fmt::format(
        L"icacls \"{}\" /remove:g *S-1-5-32-545 /c", path.wstring()));
    // read/exec
    commands.emplace_back(fmt::format(
        L"icacls \"{}\" /grant:r *S-1-5-32-545:(RX) /c", path.wstring()));

    XLOG::l.i("Protect file from User write '{}'", path);
}

void ProtectPathFromUserAccess(const fs::path &entry,
                               std::vector<std::wstring> &commands) {
    // CONTEXT: some files must be protected from the user fully
    // disable inheritance
    commands.emplace_back(
        fmt::format(L"icacls \"{}\" /inheritance:d /c", entry.wstring()));
    // remove all user rights
    commands.emplace_back(fmt::format(
        L"icacls \"{}\" /remove:g *S-1-5-32-545 /c", entry.wstring()));

    XLOG::l.i("Protect path from User access '{}'", entry);
}

namespace {
fs::path MakeCmdFileInTemp(std::string_view sub_dir, std::wstring_view name,
                           const std::vector<std::wstring> &commands) {
    try {
        auto pid = ::GetCurrentProcessId();
        static int counter = 0;
        counter++;
        const auto dir = MakeSafeTempFolder(sub_dir);
        if (dir.has_value()) {
            auto tmp_file =
                *dir / fmt::format(L"cmk_{}_{}_{}.cmd", name, pid, counter);
            std::ofstream ofs(tmp_file, std::ios::trunc);
            for (const auto &c : commands) {
                ofs << ToUtf8(c) << "\n";
            }

            return tmp_file;
        } else {
            XLOG::l("Can't create file");
            return {};
        }
    } catch (const std::exception &e) {
        XLOG::l("Exception creating file '{}'", e.what());
        return {};
    }
}
}  // namespace

class Sid {
public:
    enum class Type { admin, everyone };
    Sid(const Sid &) = delete;

    Sid(Sid &&rhs) noexcept {
        sid_ = rhs.sid_;
        type_ = rhs.type_;
        rhs.sid_ = nullptr;
    }

    Sid &operator=(const Sid &) = delete;
    Sid &operator=(Sid &&) = delete;
    explicit Sid(Type type) : type_{type} {
        switch (type_) {
            case Type::admin: {
                SID_IDENTIFIER_AUTHORITY SIDAuthNT = SECURITY_NT_AUTHORITY;
                AllocateAndInitializeSid(
                    &SIDAuthNT, 2, SECURITY_BUILTIN_DOMAIN_RID,
                    DOMAIN_ALIAS_RID_ADMINS, 0, 0, 0, 0, 0, 0, &sid_);
                break;
            }
            case Type::everyone: {
                SID_IDENTIFIER_AUTHORITY SIDAuthWorld =
                    SECURITY_WORLD_SID_AUTHORITY;
                AllocateAndInitializeSid(&SIDAuthWorld, 1, SECURITY_WORLD_RID,
                                         0, 0, 0, 0, 0, 0, 0, &sid_);
                break;
            }
        }
    }
    ~Sid() {
        if (sid_ != nullptr) {
            FreeSid(sid_);
        }
    }

    PSID sid() const { return sid_; }
    TRUSTEE_TYPE trusteeType() const {
        switch (type_) {
            case Type::admin:
                return TRUSTEE_IS_GROUP;
            case Type::everyone:
                return TRUSTEE_IS_WELL_KNOWN_GROUP;
        }
        // unreachable
        return TRUSTEE_IS_WELL_KNOWN_GROUP;
    }

private:
    PSID sid_;
    Type type_;
};

class Acl {
    class Store {
    public:
        Store(std::vector<std::pair<Sid::Type, uint32_t>> input) {
            for (const auto &[type, permission] : input) {
                auto s = Sid{type};
                sids_.emplace_back(std::move(s));
                eas_.emplace_back(EXPLICIT_ACCESS{
                    .grfAccessPermissions = permission,
                    .grfAccessMode = SET_ACCESS,
                    .grfInheritance = NO_INHERITANCE,
                    .Trustee = {
                        .TrusteeForm = TRUSTEE_IS_SID,
                        .TrusteeType = sids_.back().trusteeType(),
                        .ptstrName = static_cast<wchar_t *>(sids_.back().sid()),
                    }});
            }
        }
        std::vector<EXPLICIT_ACCESS> &eas() { return eas_; }

    private:
        std::vector<EXPLICIT_ACCESS> eas_;
        std::vector<Sid> sids_;
    };

public:
    Acl(const std::vector<std::pair<Sid::Type, uint32_t>> &input)
        : store_{input} {
        std::vector<EXPLICIT_ACCESS> &eas = store_.eas();
        if (SetEntriesInAcl(static_cast<ULONG>(eas.size()), eas.data(), nullptr,
                            &acl_) != ERROR_SUCCESS) {
            return;
        }
    }
    Acl(const Acl &) = delete;
    Acl &operator=(const Acl &) = delete;
    Acl(Acl &&) = delete;
    Acl &operator=(Acl &&) = delete;

    PACL acl() const { return acl_; }

    ~Acl() {
        if (acl_ != nullptr) {
            LocalFree(acl_);
        }
    }

private:
    Store store_;
    PACL acl_{nullptr};
};

class Sd {
public:
    Sd(const Acl &acl) {
        sd_ = (PSECURITY_DESCRIPTOR)LocalAlloc(LPTR,
                                               SECURITY_DESCRIPTOR_MIN_LENGTH);
        if (sd_ == nullptr) {
            return;
        }
        if (!InitializeSecurityDescriptor(sd_, SECURITY_DESCRIPTOR_REVISION)) {
            return;
        }
        // Add the ACL to the security descriptor.
        if (!SetSecurityDescriptorDacl(sd_,
                                       TRUE,  // bDaclPresent flag
                                       acl.acl(),
                                       FALSE))  // not a default DACL
        {
            XLOG::l("Failed to set acl");
            return;
        }
    }
    Sd(const Sd &) = delete;
    Sd &operator=(const Sd &) = delete;
    Sd(Sd &&) = delete;
    Sd &operator=(Sd &&) = delete;

    PSECURITY_DESCRIPTOR sd() const { return sd_; }
    ~Sd() {
        if (sd_ != nullptr) {
            LocalFree(sd_);
        }
    }

private:
    PSECURITY_DESCRIPTOR sd_{nullptr};
};

class SecurityAttribute {
public:
    explicit SecurityAttribute(
        const std::vector<std::pair<Sid::Type, uint32_t>> &input)
        : acl_{input}, sd_{acl_} {
        sa_.nLength = sizeof(SECURITY_ATTRIBUTES);
        sa_.lpSecurityDescriptor = sd_.sd();
        sa_.bInheritHandle = FALSE;
    }

    SECURITY_ATTRIBUTES *securityAttributes() {
        if (sa_.lpSecurityDescriptor == nullptr) {
            return nullptr;
        }
        return &sa_;
    }

private:
    Acl acl_;
    Sd sd_;
    SECURITY_ATTRIBUTES sa_;
};

std::optional<fs::path> MakeSafeTempFolder(std::string_view sub_dir) {
    SecurityAttribute sa{
        {{Sid::Type::everyone, 0}, {Sid::Type::admin, GENERIC_ALL}}};
    std::error_code ec;
    fs::remove_all(fs::temp_directory_path(ec) / sub_dir, ec);
    auto temp_folder = fs::temp_directory_path(ec) / sub_dir;
    const auto ret =
        CreateDirectoryW(temp_folder.wstring().data(), sa.securityAttributes());
    if (!ret) {
        XLOG::l("Failed to create temp folder '{}' {}", temp_folder,
                GetLastError());
        return {};
    }
    return temp_folder;
}

fs::path ExecuteCommands(std::wstring_view name,
                         const std::vector<std::wstring> &commands,
                         ExecuteMode mode) {
    XLOG::d.i("'{}' Starting executing commands [{}]", ToUtf8(name),
              commands.size());
    if (commands.empty()) {
        return {};
    }

    auto to_exec = MakeCmdFileInTemp(safe_temp_sub_dir, name, commands);
    if (!to_exec.empty()) {
        auto pid = cma::tools::RunStdCommand(to_exec.wstring(),
                                             mode == ExecuteMode::sync
                                                 ? cma::tools::WaitForEnd::yes
                                                 : cma::tools::WaitForEnd::no);
        if (pid != 0) {
            XLOG::d.i("Process is started '{}'  with pid [{}]", to_exec, pid);
            return to_exec;
        }

        XLOG::l("Process is failed to start '{}'", to_exec);
    }

    return {};
}

/// simple scanner of Win32 multi_sz strings
const wchar_t *GetMultiSzEntry(wchar_t *&pos, const wchar_t *end) {
    if (pos == nullptr || end == nullptr) {
        XLOG::l(XLOG_FUNC + "-Bad data");
        return nullptr;
    }

    if (pos >= end) {
        return nullptr;
    }

    const auto len = wcslen(pos);
    if (len == 0) {
        return nullptr;
    }

    const auto start = pos;
    pos += len + 1;
    return start;
}

std::wstring ExpandStringWithEnvironment(std::wstring_view str) {
    if (str.empty()) {
        return {};
    }

    auto log_error_and_return_default = [](std::wstring_view s) {
        XLOG::l("Can't expand the string #1 '{}' [{}]", ToUtf8(s),
                GetLastError());
        return std::wstring{s};
    };

    std::wstring result;
    auto ret = ::ExpandEnvironmentStringsW(str.data(), result.data(), 0);
    if (ret == 0) {
        return log_error_and_return_default(str);
    }

    result.resize(ret - 1);
    ret = ::ExpandEnvironmentStringsW(str.data(), result.data(), ret);
    if (ret == 0) {
        return log_error_and_return_default(str);
    }

    return result;
}

std::wstring ToCanonical(std::wstring_view raw_app_name) {
    constexpr int buf_size = 16 * 1024 + 1;
    const auto buf = std::make_unique<wchar_t[]>(buf_size);
    const auto expand_size =
        ::ExpandEnvironmentStringsW(raw_app_name.data(), buf.get(), buf_size);

    std::error_code ec;
    const auto p =
        fs::weakly_canonical(expand_size > 0 ? buf.get() : raw_app_name, ec);

    if (ec.value() == 0) {
        return p.wstring();
    }

    XLOG::d.i(
        "Path '{}' cannot be canonical: probably based on the environment variables",
        wtools::ToUtf8(raw_app_name));

    return std::wstring(raw_app_name);
}

namespace {
struct SidStore {
    [[nodiscard]] SID *sid() const noexcept { return sid_; }
    [[nodiscard]] size_t count() const noexcept { return count_; }
    bool makeAdmin() { return assignAdmin(); }
    bool makeCreator() { return assignCreator(); }
    bool makeEveryone() { return assignEveryone(); }

private:
    bool assignAdmin() {
        SID_IDENTIFIER_AUTHORITY sia_admin = SECURITY_NT_AUTHORITY;
        constexpr UCHAR count{2};

        if (::InitializeSid(sid_, &sia_admin, count) == FALSE) {
            return false;
        }
        count_ = count;
        *GetSidSubAuthority(sid_, 0) = SECURITY_BUILTIN_DOMAIN_RID;
        *GetSidSubAuthority(sid_, 1) = DOMAIN_ALIAS_RID_ADMINS;
        return true;
    }

    bool assignCreator() {
        SID_IDENTIFIER_AUTHORITY sia_creator = SECURITY_CREATOR_SID_AUTHORITY;
        constexpr UCHAR count{1};

        if (::InitializeSid(sid_, &sia_creator, count) == FALSE) {
            return false;
        }
        count_ = count;
        *GetSidSubAuthority(sid_, 0) = SECURITY_CREATOR_OWNER_RID;
        return true;
    }

    bool assignEveryone() {
        SID_IDENTIFIER_AUTHORITY sia_world = SECURITY_WORLD_SID_AUTHORITY;
        constexpr UCHAR count{1};

        if (::InitializeSid(sid_, &sia_world, count) == FALSE) {
            return false;
        }
        count_ = count;
        *GetSidSubAuthority(sid_, 0) = SECURITY_WORLD_RID;
        return true;
    }

    char buf_[32]{0};
    SID *sid_{reinterpret_cast<SID *>(buf_)};
    size_t count_{0};
};

ACL *CombineSidsIntoACl(const SidStore &first, const SidStore &second) {
    const auto acl_size =
        sizeof ACL + 2 * sizeof ACCESS_ALLOWED_ACE - sizeof DWORD +
        GetSidLengthRequired(static_cast<UCHAR>(first.count())) +
        GetSidLengthRequired(static_cast<UCHAR>(second.count()));

    // alloc
    const auto acl = static_cast<ACL *>(ProcessHeapAlloc(acl_size));

    // init
    if (acl != nullptr &&
        ::InitializeAcl(acl, static_cast<int32_t>(acl_size), ACL_REVISION) ==
            TRUE &&
        ::AddAccessAllowedAce(acl, ACL_REVISION, FILE_ALL_ACCESS,
                              first.sid()) == TRUE &&
        ::AddAccessAllowedAce(acl, ACL_REVISION, FILE_ALL_ACCESS,
                              second.sid()) == TRUE) {
        return acl;
    }
    XLOG::l("Failed ACL creation");
    ProcessHeapFree(acl);
    return nullptr;
}

}  // namespace

ACL *BuildStandardAcl() {
    SidStore everyone;
    SidStore owner;

    // initialize well known SID's
    if (!everyone.makeEveryone() || !owner.makeCreator()) {
        return nullptr;
    }

    return CombineSidsIntoACl(everyone, owner);
}

ACL *BuildAdminAcl() {
    SidStore admin;
    SidStore owner;

    // initialize well known SID's
    if (!admin.makeAdmin() || !owner.makeCreator()) {
        return nullptr;
    }

    return CombineSidsIntoACl(admin, owner);
}

SecurityAttributeKeeper::SecurityAttributeKeeper(SecurityLevel sl) {
    if (!allocAll(sl)) {
        cleanupAll();
    }
}
SecurityAttributeKeeper::~SecurityAttributeKeeper() { cleanupAll(); }

bool SecurityAttributeKeeper::allocAll(SecurityLevel sl) {
    // this trash is referenced in the Security
    // Descriptor, we should keep it safe
    switch (sl) {
        case SecurityLevel::standard:
            acl_ = BuildStandardAcl();
            break;
        case SecurityLevel::admin:
            acl_ = BuildAdminAcl();
            break;
    }

    sd_ = static_cast<SECURITY_DESCRIPTOR *>(
        ProcessHeapAlloc(sizeof SECURITY_DESCRIPTOR));
    sa_ = static_cast<SECURITY_ATTRIBUTES *>(
        ProcessHeapAlloc(sizeof SECURITY_ATTRIBUTES));

    if (acl_ != nullptr && sd_ != nullptr &&
        sa_ != nullptr &&  // <--- alloc check
        ::InitializeSecurityDescriptor(sd_, SECURITY_DESCRIPTOR_REVISION) ==
            TRUE &&
        ::SetSecurityDescriptorDacl(sd_, TRUE, acl_, FALSE) == TRUE) {
        sa_->nLength = sizeof SECURITY_ATTRIBUTES;
        sa_->lpSecurityDescriptor = sd_;
        sa_->bInheritHandle = FALSE;
        return true;
    }
    return false;
}
void SecurityAttributeKeeper::cleanupAll() {
    ProcessHeapFree(acl_);
    ProcessHeapFree(sd_);
    ProcessHeapFree(sa_);
    acl_ = nullptr;
    sd_ = nullptr;
    sa_ = nullptr;
}

std::wstring SidToName(std::wstring_view sid, const SID_NAME_USE &sid_type) {
    constexpr DWORD buf_size = 256;
    PSID psid{nullptr};

    if (::ConvertStringSidToSid(sid.data(), &psid) == FALSE) {
        return {};
    }
    ON_OUT_OF_SCOPE(::LocalFree(psid));

    wchar_t name[buf_size];
    DWORD name_size{buf_size};
    wchar_t domain[buf_size];
    DWORD domain_size{buf_size};
    SID_NAME_USE try_sid_type{sid_type};

    if (::LookupAccountSid(nullptr, psid, name, &name_size, domain,
                           &domain_size, &try_sid_type)) {
        return name;
    }
    return {};
}

namespace {

std::pair<size_t, bool> ReadHandle(std::span<char> buffer, HANDLE h) {
    const auto store = buffer.data();
    DWORD read_in_fact = 0;
    const auto count = static_cast<DWORD>(buffer.size());
    return {read_in_fact, ::ReadFile(h, store, count, &read_in_fact, nullptr)};
}

// add content of file to the buffer
bool AppendHandleContent(std::vector<char> &buffer, HANDLE h,
                         size_t count) noexcept {
    const auto buf_size = buffer.size();
    try {
        buffer.resize(buf_size + count);
    } catch (const std::exception &e) {
        XLOG::l(" exception: '{}'", e.what());
        return false;
    }
    auto [read_in_fact, success] =
        ReadHandle(std::span{buffer.data() + buf_size, count}, h);
    if (!success) {
        return false;
    }

    if (read_in_fact != count) {
        buffer.resize(buf_size + read_in_fact);
    }

    return true;
}
}  // namespace

std::vector<char> ReadFromHandle(HANDLE handle) {
    std::vector<char> buf;
    while (true) {
        const auto read_count = DataCountOnHandle(handle);
        if (read_count == 0) {  // no data or error
            break;
        }
        if (!AppendHandleContent(buf, handle, read_count)) {
            break;
        }
    }
    return buf;
}

std::string ReplaceBlankLineWithSeparator(const std::string &raw,
                                          std::string_view separator) {
    if (raw.empty()) {
        return raw;
    }

    if (raw == "\n") {
        return std::string(separator) + "\n";
    }

    // Remove trailing '\n' to avoid synthetic empty row from split
    std::string_view data = raw;
    const bool had_trailing_nl = raw.back() == '\n';
    if (had_trailing_nl) {
        data.remove_suffix(1);
    }

    auto is_blank = [](const auto &rng) {
        return std::ranges::all_of(
            rng, [](unsigned char c) { return std::isspace(c); });
    };

    auto processed_lines =
        data | std::views::split('\n') |
        std::views::transform([is_blank, separator](const auto &line) {
            if (is_blank(line)) {
                return std::string(separator);
            }
            return std::string(line.begin(), line.end());
        });

    std::string result;
    bool first = true;
    for (const auto &line : processed_lines) {
        if (!first) {
            result.push_back('\n');
        }
        first = false;
        result.append(line);
    }

    if (had_trailing_nl && !result.empty()) {
        result.push_back('\n');
    }

    return result;
}

std::string RunCommand(std::wstring_view cmd) {
    AppRunner ar;
    const auto ret = ar.goExecAsJob(cmd);
    if (ret == 0) {
        XLOG::d("Failed to run '{}'", ToUtf8(cmd));
        return {};
    }
    const auto pid = ar.processId();
    auto timeout = 20'000ms;
    constexpr auto grane = 50ms;
    std::string r;
    while (true) {
        auto [code, error] = GetProcessExitCode(pid);
        if (code != 0 && code != STATUS_PENDING) {
            XLOG::l("RunCommand '{}' fails with code [{}] and error [{}]",
                    ToUtf8(cmd), code, error);
            break;
        }
        auto result = ReadFromHandle(ar.getStdioRead());
        r += std::string{result.begin(), result.end()};
        std::this_thread::sleep_for(grane);
        timeout = timeout - grane;
        if (timeout <= 0s || code == 0) {
            break;
        }
    }

    return r;
}

std::string_view TcpStateToName(unsigned long state) noexcept {
    switch (state) {
        case MIB_TCP_STATE_CLOSED:
            return "CLOSED";
        case MIB_TCP_STATE_LISTEN:
            return "LISTEN";
        case MIB_TCP_STATE_SYN_SENT:
            return "SYN-SENT";
        case MIB_TCP_STATE_SYN_RCVD:
            return "SYN-RECEIVED";
        case MIB_TCP_STATE_ESTAB:
            return "ESTABLISHED";
        case MIB_TCP_STATE_FIN_WAIT1:
            return "FIN-WAIT-1";
        case MIB_TCP_STATE_FIN_WAIT2:
            return "FIN-WAIT-2 ";
        case MIB_TCP_STATE_CLOSE_WAIT:
            return "CLOSE-WAIT";
        case MIB_TCP_STATE_CLOSING:
            return "CLOSING";
        case MIB_TCP_STATE_LAST_ACK:
            return "LAST-ACK";
        case MIB_TCP_STATE_TIME_WAIT:
            return "TIME-WAIT";
        case MIB_TCP_STATE_DELETE_TCB:
            return "DELETE-TCB";
        default:
            return "UNKNOWN";
    }
}

namespace {
class MibTcpTable2Wrapper {
public:
    MibTcpTable2Wrapper() {
        auto size = static_cast<DWORD>(sizeof MIB_TCPTABLE2);
        reallocateBuffer(size);

        while (true) {
            const auto ret = ::GetTcpTable2(table_, &size, TRUE);
            switch (ret) {
                case ERROR_INSUFFICIENT_BUFFER:
                    reallocateBuffer(size);
                    continue;
                case ERROR_SUCCESS:
                    return;
                default:
                    ::operator delete(static_cast<void *>(table_));
                    table_ = nullptr;
                    XLOG::l("Error [{}] GetTcpTable2", ret);
                    return;
            }
        }
    }

    MibTcpTable2Wrapper(const MibTcpTable2Wrapper &) = delete;
    MibTcpTable2Wrapper &operator=(const MibTcpTable2Wrapper &) = delete;
    MibTcpTable2Wrapper(MibTcpTable2Wrapper &&) = delete;
    MibTcpTable2Wrapper &operator=(MibTcpTable2Wrapper &&) = delete;

    ~MibTcpTable2Wrapper() { ::operator delete(static_cast<void *>(table_)); }

    [[nodiscard]] const MIB_TCPROW2 *row(size_t index) const {
        return table_ == nullptr || index >= table_->dwNumEntries
                   ? nullptr
                   : table_->table + index;
    }
    [[nodiscard]] size_t count() const {
        return table_ == nullptr ? 0U : table_->dwNumEntries;
    }

private:
    void reallocateBuffer(size_t size) {
        ::operator delete(static_cast<void *>(table_));
        table_ = static_cast<MIB_TCPTABLE2 *>(::operator new(size));
    }

    MIB_TCPTABLE2 *table_{nullptr};
};
}  // namespace

bool CheckProcessUsePort(uint16_t port, uint32_t pid, uint16_t peer_port) {
    const auto p_port = ::htons(peer_port);
    const auto r_port = ::htons(port);
    const MibTcpTable2Wrapper table;
    for (size_t i = 0; i < table.count(); ++i) {
        const auto *row = table.row(i);
        if (row == nullptr) {
            break;
        }
        const auto &entry = *row;
        if (entry.dwRemotePort == r_port && entry.dwLocalPort == p_port &&
            pid == entry.dwOwningPid) {
            XLOG::d.i(
                "Peer/local {:>6} remote {:>6} state {:10} from pid {:>6}",
                p_port, r_port, TcpStateToName(entry.dwState),
                entry.dwOwningPid);
            return true;
        }
    }
    return false;
}

std::optional<uint32_t> GetConnectionPid(uint16_t port, uint16_t peer_port) {
    const auto p_port = ::htons(peer_port);
    const auto r_port = ::htons(port);
    const MibTcpTable2Wrapper table;
    for (size_t i = 0; i < table.count(); ++i) {
        const auto *row = table.row(i);
        if (row == nullptr) {
            break;
        }
        if (row->dwRemotePort == r_port && row->dwLocalPort == p_port) {
            return row->dwOwningPid;
        }
    }
    return {};
}

#if 0
/// <summary>
///  The code below is a reference code from MSDN
/// </summary>
ACL* BuildAdminSDAcls {
    DWORD dwRes, dwDisposition;
    PSID pEveryoneSID = NULL, pAdminSID = NULL;
    PACL pACL = NULL;
    PSECURITY_DESCRIPTOR pSD = NULL;
    EXPLICIT_ACCESS ea[2];
    SID_IDENTIFIER_AUTHORITY SIDAuthWorld = SECURITY_WORLD_SID_AUTHORITY;
    SID_IDENTIFIER_AUTHORITY SIDAuthNT = SECURITY_NT_AUTHORITY;
    SECURITY_ATTRIBUTES sa;
    LONG lRes;
    HKEY hkSub = NULL;

    // Create a well-known SID for the Everyone group.
    if (!AllocateAndInitializeSid(&SIDAuthWorld, 1, SECURITY_WORLD_RID, 0, 0, 0,
                                  0, 0, 0, 0, &pEveryoneSID)) {
        _tprintf(_T("AllocateAndInitializeSid Error %u\n"), GetLastError());
        goto Cleanup;
    }

    // Initialize an EXPLICIT_ACCESS structure for an ACE.
    // The ACE will allow Everyone read access to the key.
    ZeroMemory(&ea, 2 * sizeof EXPLICIT_ACCESS);
    ea[0].grfAccessPermissions = KEY_READ;
    ea[0].grfAccessMode = SET_ACCESS;
    ea[0].grfInheritance = NO_INHERITANCE;
    ea[0].Trustee.TrusteeForm = TRUSTEE_IS_SID;
    ea[0].Trustee.TrusteeType = TRUSTEE_IS_WELL_KNOWN_GROUP;
    ea[0].Trustee.ptstrName = (LPTSTR)pEveryoneSID;

    // Create a SID for the BUILTIN\Administrators group.
    if (!AllocateAndInitializeSid(&SIDAuthNT, 2, SECURITY_BUILTIN_DOMAIN_RID,
                                  DOMAIN_ALIAS_RID_ADMINS, 0, 0, 0, 0, 0, 0,
                                  &pAdminSID)) {
        _tprintf(_T("AllocateAndInitializeSid Error %u\n"), GetLastError());
        goto Cleanup;
    }

    // Initialize an EXPLICIT_ACCESS structure for an ACE.
    // The ACE will allow the Administrators group full access to
    // the key.
    ea[1].grfAccessPermissions = KEY_ALL_ACCESS;
    ea[1].grfAccessMode = SET_ACCESS;
    ea[1].grfInheritance = NO_INHERITANCE;
    ea[1].Trustee.TrusteeForm = TRUSTEE_IS_SID;
    ea[1].Trustee.TrusteeType = TRUSTEE_IS_GROUP;
    ea[1].Trustee.ptstrName = (LPTSTR)pAdminSID;

    // Create a new ACL that contains the new ACEs.
    dwRes = SetEntriesInAcl(2, ea, NULL, &pACL);
    if (ERROR_SUCCESS != dwRes) {
        _tprintf(_T("SetEntriesInAcl Error %u\n"), GetLastError());
        goto Cleanup;
    }

    // Initialize a security descriptor.
    pSD =
        (PSECURITY_DESCRIPTOR)LocalAlloc(LPTR, SECURITY_DESCRIPTOR_MIN_LENGTH);
    if (NULL == pSD) {
        _tprintf(_T("LocalAlloc Error %u\n"), GetLastError());
        goto Cleanup;
    }

    if (!InitializeSecurityDescriptor(pSD, SECURITY_DESCRIPTOR_REVISION)) {
        _tprintf(_T("InitializeSecurityDescriptor Error %u\n"), GetLastError());
        goto Cleanup;
    }

    // Add the ACL to the security descriptor.
    if (!SetSecurityDescriptorDacl(pSD,
                                   TRUE,  // bDaclPresent flag
                                   pACL,
                                   FALSE))  // not a default DACL
    {
        _tprintf(_T("SetSecurityDescriptorDacl Error %u\n"), GetLastError());
        goto Cleanup;
    }

    // Initialize a security attributes structure.
    sa.nLength = sizeof SECURITY_ATTRIBUTES;
    sa.lpSecurityDescriptor = pSD;
    sa.bInheritHandle = FALSE;

    // Use the security attributes to set the security descriptor
    // when you create a key.
    lRes = RegCreateKeyEx(HKEY_CURRENT_USER, _T("mykey"), 0, _T(""), 0,
                          KEY_READ | KEY_WRITE, &sa, &hkSub, &dwDisposition);
    _tprintf(_T("RegCreateKeyEx result %u\n"), lRes);

Cleanup:

    if (pEveryoneSID) FreeSid(pEveryoneSID);
    if (pAdminSID) FreeSid(pAdminSID);
    if (pACL) LocalFree(pACL);
    if (pSD) LocalFree(pSD);
    if (hkSub) RegCloseKey(hkSub);

    return;
}

#endif
namespace {
class ServiceControl {
public:
    enum class Mode { query, control };
    ServiceControl(std::wstring_view service_name, Mode mode) {
        openService(service_name, mode);
    }

    ServiceControl(const ServiceControl &) = delete;
    ServiceControl(ServiceControl &&) = delete;
    ServiceControl &operator=(const ServiceControl &) = delete;
    ServiceControl &operator=(ServiceControl &&) = delete;

    ~ServiceControl() noexcept {
        if (manager_ != nullptr) {
            ::CloseServiceHandle(manager_);
        }
        if (service_ != nullptr) {
            ::CloseServiceHandle(service_);
        }
    }
    [[nodiscard]] uint32_t getStatus() const noexcept;

protected:
    void openService(std::wstring_view service_name, Mode mode);
    static uint32_t flagsFromMode(Mode mode);

private:
    SC_HANDLE manager_{nullptr};
    SC_HANDLE service_{nullptr};
    unsigned long error_{0U};
};

uint32_t ServiceControl::flagsFromMode(Mode mode) {
    switch (mode) {
        case Mode::control:
            return SERVICE_STOP | SERVICE_START | SERVICE_QUERY_STATUS |
                   SERVICE_ENUMERATE_DEPENDENTS;
        case Mode::query:
            return SERVICE_QUERY_STATUS | SERVICE_ENUMERATE_DEPENDENTS;
    }
    // unreachable
    return 0U;
}

void ServiceControl::openService(std::wstring_view service_name, Mode mode) {
    manager_ = ::OpenSCManager(nullptr,  // local computer
                               nullptr,  // ServicesActive database
                               SC_MANAGER_ALL_ACCESS);
    if (manager_ == nullptr) {
        error_ = ::GetLastError();
        XLOG::l("OpenSCManager failed [{}]", error_);
        return;
    }
    service_ = ::OpenService(manager_,  // SCM database
                             service_name.data(), flagsFromMode(mode));
    if (service_ == nullptr) {
        error_ = ::GetLastError();
        XLOG::l("OpenService '{}' failed [{}]", wtools::ToUtf8(service_name),
                error_);
    }
}

uint32_t ServiceControl::getStatus() const noexcept {
    if (service_ == nullptr) {
        return 0;
    }
    DWORD bytes_needed = 0;
    SERVICE_STATUS_PROCESS ssp;
    const auto buffer = reinterpret_cast<BYTE *>(&ssp);

    if (::QueryServiceStatusEx(service_, SC_STATUS_PROCESS_INFO, buffer,
                               sizeof SERVICE_STATUS_PROCESS,
                               &bytes_needed) == FALSE) {
        XLOG::l("QueryServiceStatusEx failed [{}]", ::GetLastError());
        return 0;
    }
    return ssp.dwCurrentState;
}
}  // namespace

uint32_t GetServiceStatus(const std::wstring &name) noexcept {
    const ServiceControl sc(name, ServiceControl::Mode::query);
    return sc.getStatus();
}

InternalUser InternalUsersDb::obtainUser(std::wstring_view group) {
    const std::wstring group_name(group);
    std::lock_guard lk(users_lock_);

    if (auto it = users_.find(group_name); it != users_.end()) {
        return it->second;
    }

    auto iu = CreateCmaUserInGroup(group_name);
    if (iu.first.empty()) {
        return {};
    }

    users_[group_name] = iu;

    return iu;
}

void InternalUsersDb::killAll() {
    if (cma::GetModus() == cma::Modus::service) {
        XLOG::d.i("service doesn't delete own users");
        return;
    }

    std::lock_guard lk(users_lock_);
    for (const auto &iu : users_ | std::views::values) {
        RemoveCmaUser(iu.first);
    }
    users_.clear();
}

size_t InternalUsersDb::size() const {
    std::lock_guard lk(users_lock_);
    return users_.size();
}

inline std::string ToUtf8(const std::wstring_view src,
                          unsigned long &error_code) noexcept {
    const auto in_len = static_cast<int>(src.length());
    const auto out_len = ::WideCharToMultiByte(CP_UTF8, 0, src.data(), in_len,
                                               nullptr, 0, nullptr, nullptr);
    if (out_len == 0) {
        error_code = ::GetLastError();
        return {};
    }

    std::string str;
    str.resize(out_len);

    const auto result = ::WideCharToMultiByte(
        CP_UTF8, WC_ERR_INVALID_CHARS, src.data(), static_cast<int>(src.size()),
        str.data(), out_len, nullptr, nullptr);
    if (result == 0) {
        error_code = ::GetLastError();
        return {};
    }
    // some older engines may have problems if we do not have trailing zero
    AddSafetyEndingNull(str);
    return str;
}

std::optional<uint64_t> _to_speed(uint64_t speed) {
    return speed == 0xFFFF'FFFF'FFFF'FFFF ? std::nullopt : std::optional{speed};
}

std::string DecodeMac(const IP_ADAPTER_ADDRESSES &a) {
    if (a.PhysicalAddressLength == 0) {
        // backward compatibility for devices with no physical address
        return "00:00:00:00:00:00:00:00";
    }

    const auto *begin = std::begin(a.PhysicalAddress);
    const auto *end = begin + a.PhysicalAddressLength;

    return std::accumulate(std::next(begin), end, fmt::format("{:02X}", *begin),
                           [](std::string acc, BYTE b) {
                               acc += fmt::format(":{:02X}", b);
                               return acc;
                           });
}

AdapterInfo ToAdapterInfo(const IP_ADAPTER_ADDRESSES &a) {
    const auto address = DecodeMac(a);
    return AdapterInfo{
        .guid{a.AdapterName},
        .friendly_name{a.FriendlyName},
        .description{a.Description},
        .if_type{a.IfType},
        .receive_speed{_to_speed(a.ReceiveLinkSpeed)},
        .transmit_speed{_to_speed(a.TransmitLinkSpeed)},
        .oper_status{a.OperStatus},
        .mac_address{address},
    };
}

using AdapterInfoStore = std::unordered_map<std::wstring, AdapterInfo>;

std::wstring MangleNameForPerfCounter(std::wstring_view name) noexcept {
    std::wstring output{name};
    for (auto &c : output) {
        switch (c) {
            case L'(':
                c = L'[';
                break;
            case L')':
                c = L']';
                break;
            case L'\\':
            case L'/':
            case L'#':
                c = L'_';
                break;
        }
    }
    return output;
}

AdapterInfoStore GetAdapterInfoStore() {
    constexpr auto max_interfaces = 500;
    const auto buffer =
        std::make_unique<IP_ADAPTER_ADDRESSES[]>(max_interfaces);

    AdapterInfoStore store;
    ULONG length = max_interfaces * sizeof(IP_ADAPTER_ADDRESSES);

    if (const auto error =
            GetAdaptersAddresses(AF_UNSPEC, GAA_FLAG_INCLUDE_ALL_INTERFACES,
                                 nullptr, buffer.get(), &length);
        error != ERROR_SUCCESS) {
        return store;
    }

    const auto head = buffer.get();
    for (auto cur = head; cur; cur = cur->Next) {
        store[MangleNameForPerfCounter(cur->Description)] = ToAdapterInfo(*cur);
    }
    return store;
}

namespace {
/// return string vector with Name and Version
/// on error empty vector
std::vector<std::wstring> GetOsRawInfo() {
    wtools::WmiWrapper wmi;
    wmi.open();
    wmi.connect(L"ROOT\\CIMV2");
    if (!wmi.impersonate()) {
        XLOG::l("Failed to impersonate");
    }
    auto [result, status] = wmi.queryTable({L"Name", L"Version"},
                                           L"Win32_OperatingSystem", L"\t", 5);
    if (status != WmiStatus::ok) {
        XLOG::l("Failed to query Win32_OperatingSystem");
        return {};
    }
    const auto rows = cma::tools::SplitString(result, L"\n");
    if (rows.size() != 2) {
        XLOG::l("Query Win32_OperatingSystem returns bad data {}",
                wtools::ToUtf8(result));
        return {};
    }
    auto values = cma::tools::SplitString(rows[1], L"\t");
    if (values.size() != 2) {
        XLOG::l("Query Win32_OperatingSystem returns bad data {}",
                wtools::ToUtf8(result));
        return {};
    }
    const auto name_and_dirs = cma::tools::SplitString(values[0], L"|");

    // contains smth like:
    // Microsoft Windows 10 Pro|C:\Windows|\Device\Harddisk0\Partition3
    values[0] = name_and_dirs[0];

    return values;
}
}  // namespace

std::optional<OsInfo> GetOsInfo() {
    static auto os_info = GetOsRawInfo();
    if (os_info.empty()) {
        os_info = GetOsRawInfo();
    }
    if (os_info.empty()) {
        return {};
    }
    return OsInfo{.name = os_info[0], .version = os_info[1]};
}

std::optional<std::tm> GetTimeAsTm(
    std::chrono::system_clock::time_point time_point) {
    const auto in_time_t = std::chrono::system_clock::to_time_t(time_point);
    std::tm buf{};

    if (const auto result = ::localtime_s(&buf, &in_time_t); result != 0) {
        XLOG::d.e("GetTimeAsTm: localtime_s failed with result {}", result);
        return std::nullopt;
    }

    return buf;
}

///  tested indirectly
std::optional<std::wstring> FindUserName(const PSID sid) {
    if (sid == nullptr) {
        return {};
    }
    WCHAR name[256];
    WCHAR domain[256];
    DWORD cchName = 256;
    DWORD cchDomain = 256;
    SID_NAME_USE use;
    if (LookupAccountSidW(nullptr, sid, name, &cchName, domain, &cchDomain,
                          &use)) {
        return name;
    }

    return std::nullopt;
}

}  // namespace wtools

// verified code from the legacy client
SOCKET
RemoveSocketInheritance(SOCKET socket) {
    HANDLE new_handle = nullptr;

    ::DuplicateHandle(::GetCurrentProcess(), reinterpret_cast<HANDLE>(socket),
                      ::GetCurrentProcess(), &new_handle, 0, FALSE,
                      DUPLICATE_CLOSE_SOURCE | DUPLICATE_SAME_ACCESS);

    return reinterpret_cast<SOCKET>(new_handle);
}

//
// replaces WSASocketW in asio.hpp
// This is BAD method, still we have no other choice
//
SOCKET WSASocketW_Hook(int af, int type, int protocol,
                       LPWSAPROTOCOL_INFOW protocol_info, GROUP g,
                       DWORD flags) {
    const auto handle =
        ::WSASocketW(af, type, protocol, protocol_info, g, flags);
    if (handle == INVALID_SOCKET) {
        XLOG::l("Error on socket creation {}", GetLastError());
        return handle;
    }

    return RemoveSocketInheritance(handle);
}
