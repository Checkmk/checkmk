// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// wtools.h
//
// Windows Specific Tools
//
#pragma once

#ifndef WTOOLS_H
#define WTOOLS_H

#include <WinSock2.h>  // here to help iphlpapi.h

#define _WIN32_DCOM  // NOLINT

#include <AclAPI.h>
#include <TlHelp32.h>
#include <WbemIdl.h>
#include <comdef.h>
#include <iphlpapi.h>

#include <atomic>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <tuple>

#include "Windows.h"
#include "datablock.h"
#include "tools/_win.h"
#include "tools/_xlog.h"
#include "winperf.h"

namespace wtools {
constexpr std::string_view safe_temp_sub_dir = "cmk_service";

inline void *ProcessHeapAlloc(size_t size) noexcept {
    return ::HeapAlloc(::GetProcessHeap(), HEAP_ZERO_MEMORY, size);
}

inline void ProcessHeapFree(void *data) noexcept {
    if (data != nullptr) {
        ::HeapFree(::GetProcessHeap(), 0, data);
    }
}

enum class SecurityLevel { standard, admin };

// RAII class to keep MS Windows Security Descriptor temporary
class SecurityAttributeKeeper {
public:
    explicit SecurityAttributeKeeper(SecurityLevel sl);
    SecurityAttributeKeeper(const SecurityAttributeKeeper &) = delete;
    SecurityAttributeKeeper &operator=(const SecurityAttributeKeeper &) =
        delete;
    SecurityAttributeKeeper(SecurityAttributeKeeper &&) = delete;
    SecurityAttributeKeeper &operator=(SecurityAttributeKeeper &&) = delete;

    ~SecurityAttributeKeeper();

    [[nodiscard]] const SECURITY_ATTRIBUTES *get() const noexcept {
        return sa_;
    }
    SECURITY_ATTRIBUTES *get() noexcept { return sa_; }

private:
    bool allocAll(SecurityLevel sl);
    void cleanupAll();
    // below are allocated using ProcessHeapAlloc values
    SECURITY_DESCRIPTOR *sd_{nullptr};
    SECURITY_ATTRIBUTES *sa_{nullptr};
    ACL *acl_{nullptr};
};

template <typename R>
concept LocalAllocated = requires(R *r) {
    { LocalFree(reinterpret_cast<HLOCAL>(r)) };
};

// this is functor to kill any pointer allocated with ::LocalAlloc
// usually this pointer comes from Windows API
template <LocalAllocated R>
struct LocalAllocDeleter {
    void operator()(R *r) const noexcept {
        if (r != nullptr) {
            ::LocalFree(reinterpret_cast<HLOCAL>(r));
        }
    }
};

// usage
#if (0)
LocalResource<SERVICE_FAILURE_ACTIONS> actions(
    ::WindowsApiToGetActions(handle_to_service));
#endif
//
template <LocalAllocated R>
using LocalResource = std::unique_ptr<R, LocalAllocDeleter<R>>;

struct HandleDeleter {
    using pointer = HANDLE;  // trick to use HANDLE as STL pointer
    void operator()(HANDLE h) const noexcept {
        if (h != nullptr) {
            ::CloseHandle(h);
        }
    }
};

/// Unique ptr for Windows HANDLE
using UniqueHandle = std::unique_ptr<HANDLE, HandleDeleter>;

// returns <exit_code, 0>, <0, error> or <-1, error>
std::pair<uint32_t, uint32_t> GetProcessExitCode(uint32_t pid);

[[nodiscard]] std::wstring GetProcessPath(uint32_t pid) noexcept;

[[nodiscard]] int KillProcessesByDir(const std::filesystem::path &dir) noexcept;

void KillProcessesByFullPath(const std::filesystem::path &path) noexcept;
void KillProcessesByPathEndAndPid(const std::filesystem::path &path_end,
                                  uint32_t need_pid) noexcept;
bool FindProcessByPathEndAndPid(const std::filesystem::path &path_end,
                                uint32_t need_pid) noexcept;

uint32_t GetParentPid(uint32_t pid);

//
//   FUNCTION: InstallService
//
//   PURPOSE: Install the current application as a service to the local
//   service control manager database.
//
//   PARAMETERS:
//   * service_name - the name of the service to be installed
//   * display_name - the display name of the service
//   * start_type - the service start option. This parameter can be one of
//     the following values: SERVICE_AUTO_START, SERVICE_BOOT_START,
//     SERVICE_DEMAND_START, SERVICE_DISABLED, SERVICE_SYSTEM_START.
//   * dependencies - a pointer to a double null-terminated array of null-
//     separated names of services or load ordering groups that the system
//     must start before this service.
//   * account - the name of the account under which the service runs.
//   * password - the password to the account name.
//
//   NOTE: If the function fails to install the service, it prints the error
//   in the standard output stream for users to diagnose the problem.
//
bool InstallService(const wchar_t *service_name, const wchar_t *display_name,
                    uint32_t start_type, const wchar_t *dependencies,
                    const wchar_t *account, const wchar_t *password);
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
enum class UninstallServiceMode { normal, test };
bool UninstallService(const wchar_t *service_name,
                      UninstallServiceMode uninstall_mode);

inline bool UninstallService(const wchar_t *service_name) {
    return UninstallService(service_name, UninstallServiceMode::normal);
}

enum class StopMode {
    cancel,  // cancel all global operations
    ignore,  // do nothing
};

class InternalUsersDb;

// Abstract Interface template for SERVICE PROCESSOR:
// WE ARE NOT GOING TO USE AT ALL.
// One binary - one object of one class
// This is just to check validness during initial development
class BaseServiceProcessor {
public:
    virtual ~BaseServiceProcessor() = default;
    // Standard Windows API to Service hit here
    virtual void stopService(StopMode stop_mode) = 0;
    virtual void startService() = 0;
    virtual void pauseService() = 0;
    virtual void continueService() = 0;
    virtual void shutdownService(StopMode stop_mode) = 0;
    [[nodiscard]] virtual const wchar_t *getMainLogName() const = 0;
    virtual void cleanupOnStop() {
        // may  be but not should overridden
    }

    virtual InternalUsersDb *getInternalUsers() = 0;
};

// keeps two handles
class DirectPipe {
public:
    DirectPipe() noexcept {
        sa_.lpSecurityDescriptor = &sd_;
        sa_.nLength = sizeof(SECURITY_ATTRIBUTES);
        sa_.bInheritHandle = TRUE;  // allow handle inherit for child process
    }

    DirectPipe(const DirectPipe &) = delete;
    DirectPipe &operator=(const DirectPipe &) = delete;
    DirectPipe(DirectPipe &&rhs) = delete;
    DirectPipe &operator=(DirectPipe &&rhs) = delete;

    ~DirectPipe() { shutdown(); }

    bool create() {
        // protected by lock
        std::lock_guard lk(lock_);
        if (read_ != nullptr || write_ != nullptr) {
            return true;
        }

        if (!sa_initialized_ && !initDescriptorsWithFullAccess()) {
            return false;  // really, something weird
        }

        if (::CreatePipe(&read_, &write_, &sa_, 0) == 0) {
            read_ = nullptr;
            write_ = nullptr;
            xlog::l("Failed to create pipe, %d", GetLastError()).print();
            return false;
        }

        // disable inheriting from the child
        if (SetHandleInformation(read_, HANDLE_FLAG_INHERIT, 0) == 0) {
            xlog::l("Failed to change handle information, %d", GetLastError())
                .print();
            ::CloseHandle(read_);
            ::CloseHandle(write_);
            read_ = nullptr;
            write_ = nullptr;
            return false;
        }
        xlog::v("Allocated  2 handle %p %p", read_, write_);
        return true;
    }

    void shutdown() noexcept {
        std::lock_guard lk(lock_);
        if (read_ != nullptr) {
            ::CloseHandle(read_);
            read_ = nullptr;
        }
        if (write_ != nullptr) {
            ::CloseHandle(write_);
            write_ = nullptr;
        }
    }

    HANDLE getRead() const noexcept {
        std::lock_guard lk(lock_);
        return read_;
    }
    HANDLE getWrite() const noexcept {
        std::lock_guard lk(lock_);
        return write_;
    }

    HANDLE moveWrite() noexcept {
        std::lock_guard lk(lock_);
        auto *write = write_;
        write_ = nullptr;
        return write;
    }

private:
    bool initDescriptorsWithFullAccess() {
        auto ret =
            ::InitializeSecurityDescriptor(&sd_, SECURITY_DESCRIPTOR_REVISION);
        if (ret == 0) {
            xlog::l(XLOG_FLINE + "Stupid fail").print();
            return false;
        }

        // *******************************************************
        // #TODO change access right to the owner of the process
        // below we have code from the winagent, which grants any access to
        // the object this is quite dangerous
        // NOW THIS IS BY DESIGN of Checkmk
        // https://docs.microsoft.com/de-at/windows/desktop/SecAuthZ/creating-a-security-descriptor-for-a-new-object-in-c--
        // ******************************************************
        ret = ::SetSecurityDescriptorDacl(&sd_, 1, nullptr, 0);  // NOLINT
        if (ret == 0) {
            xlog::l(XLOG_FLINE + "Not so stupid fail %d", GetLastError())
                .print();
            return false;
        }
        sa_initialized_ = true;
        return true;
    }
    mutable std::mutex lock_;
    HANDLE read_{nullptr};
    HANDLE write_{nullptr};
    bool sa_initialized_{false};
    SECURITY_DESCRIPTOR sd_ = {};
    SECURITY_ATTRIBUTES sa_ = {};
};

enum class ScanAction { terminate, advance };

// scans all processes in system and calls action
// returns false on error
// based on ToolHelp api family
// normally require elevation
// if action returns false, scan will be stopped(this is only optimization)
bool ScanProcessList(
    const std::function<ScanAction(const PROCESSENTRY32 &)> &action);

// standard process terminator
bool KillProcess(uint32_t pid, int exit_code) noexcept;

// process terminator
// used to kill OpenHardwareMonitor
bool KillProcess(std::wstring_view process_name, int exit_code) noexcept;

// special function to kill suspicious processes with all here children
// useful mostly to stop legacy agent which may have plugins running
bool KillProcessFully(const std::wstring &process_name, int exit_code) noexcept;

// calculates count of processes in the system
int FindProcess(std::wstring_view process_name) noexcept;

constexpr bool kProcessTreeKillAllowed = false;

// WIN32 described method of killing process tree
void KillProcessTree(uint32_t process_id);

class AppRunner {
public:
    AppRunner() = default;
    // no copy, no move
    AppRunner(const AppRunner &) = delete;
    AppRunner(AppRunner &&) = delete;
    AppRunner &operator=(const AppRunner &) = delete;
    AppRunner &operator=(AppRunner &&) = delete;

    ~AppRunner() {
        kill(true);
        stdio_.shutdown();
        stderr_.shutdown();
    }

    // returns process id
    uint32_t goExecAsJob(std::wstring_view command_line) noexcept;

    /// returns process id
    uint32_t goExecAsJobAndUser(std::wstring_view user,
                                std::wstring_view password,
                                std::wstring_view command_line) noexcept;
    /// returns process id
    uint32_t goExecAsDetached(std::wstring_view command_line) noexcept;
    /// returns process id
    uint32_t goExecAsController(std::wstring_view command_line) noexcept;

    void kill(bool kill_tree_too) {
        auto proc_id = process_id_.exchange(0);
        if (proc_id == 0) {
            xlog::v(
                "Attempt to kill process which is not started or already killed");
            return;
        }

        if (kill_tree_too) {
            if (job_handle_ != nullptr) {
                // this is normal case but with job
                TerminateJobObject(job_handle_, 0);

                // job:
                CloseHandle(job_handle_);
                job_handle_ = nullptr;

                // process:
                if (process_handle_ != nullptr) {
                    ::CloseHandle(process_handle_);  // must
                    process_handle_ = nullptr;
                }
            } else {
                if constexpr (kProcessTreeKillAllowed) {
                    KillProcessTree(proc_id);
                }
            }

            return;
        }

        if (exit_code_ == STILL_ACTIVE && !KillProcess(proc_id, -1)) {
            xlog::v("Failed kill {} status {}", proc_id, GetLastError());
        }
    }

    auto getCmdLine() const noexcept { return cmd_line_; }
    auto processId() const noexcept { return process_id_.load(); }
    auto exitCode() const noexcept { return exit_code_; }
    auto getStdioRead() const noexcept { return stdio_.getRead(); }
    auto getStderrRead() const noexcept { return stderr_.getRead(); }

    const auto &getData() const noexcept { return data_; }
    auto &getData() noexcept { return data_; }

    bool trySetExitCode(uint32_t pid, uint32_t code) noexcept {
        if (pid != 0U && pid == process_id_) {
            exit_code_ = code;
            return true;
        }
        return false;
    }

private:
    enum class UsePipe { yes, no };
    uint32_t goExec(std::wstring_view command_line, UsePipe use_pipe) noexcept;

    void prepareResources(std::wstring_view command_line,
                          bool create_pipe) noexcept;
    void cleanResources() noexcept;
    void setExitCode(uint32_t code) noexcept { exit_code_ = code; }
    std::wstring cmd_line_;
    std::atomic<uint32_t> process_id_{0};
    HANDLE job_handle_{nullptr};
    HANDLE process_handle_{nullptr};
    DirectPipe stdio_;
    DirectPipe stderr_;

    // output
    std::vector<char> data_;
    uint32_t exit_code_{STILL_ACTIVE};
};

class ServiceController final {
    static std::mutex s_lock_;
    static ServiceController *s_controller_;  // probably we need her shared
                                              // ptr, but this is clear overkill
public:
    explicit ServiceController(std::unique_ptr<BaseServiceProcessor> processor);

    ServiceController(const ServiceController &) = delete;
    ServiceController &operator=(const ServiceController &) = delete;
    ServiceController(ServiceController &&) = delete;
    ServiceController &operator=(ServiceController &&) = delete;

    ~ServiceController() {
        std::lock_guard lk(s_lock_);
        if (s_controller_ != nullptr && s_controller_ == this) {
            s_controller_ = nullptr;
        }
    }

    // no return from here till service ends
    enum class StopType { normal, no_connect, fail };
    StopType registerAndRun(const wchar_t *service_name, bool can_stop,
                            bool can_shutdown, bool can_pause_continue);
    StopType registerAndRun(const wchar_t *service_name) {
        return registerAndRun(service_name, true, true, true);
    }

    const BaseServiceProcessor *processor() const { return processor_.get(); }

protected:
    void setServiceStatus(DWORD current_state, DWORD win32_exit_code,
                          DWORD wait_hint);
    void setServiceStatus(DWORD current_state) {
        return setServiceStatus(current_state, NO_ERROR, 0);
    }

private:
    void initStatus(bool can_stop, bool can_shutdown, bool can_pause_continue);

    // Entry point for the service. It registers the handler function for
    // the service and starts the service. NO RETURN FROM HERE when service
    // running.
    static void WINAPI ServiceMain(DWORD argc, wchar_t **argv);

    void Start(DWORD argc, wchar_t **argv);
    void Stop();
    void Shutdown();
    void Pause();
    void Continue();

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
    static void WINAPI ServiceCtrlHandler(DWORD control_code);

    // used to trace calls in debug mode, not used in production
    static DWORD WINAPI ServiceCtrlHandlerEx(DWORD control_code,
                                             DWORD event_type, void *event_data,
                                             void *context);

    // The singleton service instance.
    std::unique_ptr<BaseServiceProcessor> processor_;

    std::unique_ptr<wchar_t[]> name_;

    SERVICE_STATUS status_ = {};
    SERVICE_STATUS_HANDLE status_handle_{nullptr};
};

/// Converts string to UTF-8 with error code
/// Returns empty string on error.
inline std::string ToUtf8(const std::wstring_view src,
                          unsigned long &error_code) noexcept;

/// Converts to UTF-8 drops error code
/// This default API used. In most cases we could treat malformed UTF-8 as empty
/// strings
inline std::string ToUtf8(const std::wstring_view src) noexcept {
    unsigned long _ = 0;
    return ToUtf8(src, _);
}

/// Converts  CP to UTF-8
inline std::string oemToUtf8(
    std::string_view oem, std::optional<UINT> cp_opt = std::nullopt) noexcept {
    UINT cp = cp_opt.has_value() ? *cp_opt : GetConsoleCP();

    auto wlen = MultiByteToWideChar(cp, 0, oem.data(), -1, nullptr, 0);
    if (wlen == 0) {
        return {};
    }

    auto wide = std::make_unique<wchar_t[]>(wlen);
    if (MultiByteToWideChar(cp, 0, oem.data(), -1, wide.get(), wlen) > 0) {
        return ToUtf8(wide.get());
    }

    return {};
}

inline std::string ToUtf8(std::string_view src) noexcept {
    return std::string{src};
}

/// Converts correctly path to string using conversion form wchar to utf8
inline std::string ToStr(const std::filesystem::path &src) noexcept {
    return ToUtf8(src.wstring());
}

std::wstring ToCanonical(std::wstring_view raw_app_name);
// standard Windows converter from Microsoft
// WINDOWS ONLY
inline std::wstring ConvertToUtf16(std::string_view src) noexcept {
    const auto in_len = static_cast<int>(src.length());
    const auto *utf8_str = src.data();
    const auto out_len =
        MultiByteToWideChar(CP_UTF8, 0, utf8_str, in_len, nullptr, 0);
    std::wstring wstr;
    wstr.resize(out_len);

    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, utf8_str, in_len,
                            wstr.data(), out_len) == out_len) {
        return wstr;
    }
    return {};
}

namespace perf {

using NameMap = std::unordered_map<unsigned long, std::wstring>;

// read MULTI_SZ string from the registry
enum class PerfCounterReg { national, english };
std::vector<wchar_t> ReadPerfCounterKeyFromRegistry(PerfCounterReg type);
std::optional<uint32_t> FindPerfIndexInRegistry(std::wstring_view key);
NameMap GenerateNameMap();

using DataSequence = cma::tools::DataBlock<BYTE>;

// API:
// 1. Read data from registry
DataSequence ReadPerformanceDataFromRegistry(
    const std::wstring &counter_name) noexcept;

// 2. Find required object
const PERF_OBJECT_TYPE *FindPerfObject(const DataSequence &data_buffer,
                                       DWORD counter_index) noexcept;

// 3. Get Instances and Names of Instances
std::vector<const PERF_INSTANCE_DEFINITION *> GenerateInstances(
    const PERF_OBJECT_TYPE *object) noexcept;
std::vector<std::wstring> GenerateInstanceNames(
    const PERF_OBJECT_TYPE *object) noexcept;

// 4. Get Counters
// INSTANCELESS!
std::vector<const PERF_COUNTER_DEFINITION *> GenerateCounters(
    const PERF_OBJECT_TYPE *object,
    const PERF_COUNTER_BLOCK *&data_block) noexcept;

// INSTANCED
std::vector<const PERF_COUNTER_DEFINITION *> GenerateCounters(
    const PERF_OBJECT_TYPE *object) noexcept;

// NAMES
std::vector<std::wstring> GenerateCounterNames(const PERF_OBJECT_TYPE *object,
                                               const NameMap &name_map);
// 5. And Values!
std::vector<uint64_t> GenerateValues(
    const PERF_COUNTER_DEFINITION &counter,
    const std::vector<const PERF_INSTANCE_DEFINITION *> &instances) noexcept;

uint64_t GetValueFromBlock(const PERF_COUNTER_DEFINITION &counter,
                           const PERF_COUNTER_BLOCK *block) noexcept;

std::string GetName(uint32_t counter_type) noexcept;
}  // namespace perf

inline int64_t QueryPerformanceFreq() noexcept {
    LARGE_INTEGER frequency;
    ::QueryPerformanceFrequency(&frequency);
    return frequency.QuadPart;
}

inline int64_t QueryPerformanceCo() noexcept {
    LARGE_INTEGER counter;
    ::QueryPerformanceCounter(&counter);
    return counter.QuadPart;
}

/// to get in windows find path to your binary
/// MAY NOT WORK when you are running as a service
std::filesystem::path GetCurrentExePath();

/// wrapper for win32 specific function
/// return 0 when no data or error
inline int DataCountOnHandle(HANDLE handle) noexcept {
    DWORD read_count = 0;
    // MSDN says to do so
    if (::PeekNamedPipe(handle, nullptr, 0, nullptr, &read_count, nullptr) ==
        0) {
        return 0;
    }

    return read_count;
}

// TODO(sk): remove it as a deprecated
template <typename T>
bool IsVectorMarkedAsUTF16(const std::vector<T> &data) noexcept {
    static_assert(sizeof(T) == 1, "Invalid Data Type in template");
    constexpr auto char_0 = static_cast<T>('\xFF');
    constexpr auto char_1 = static_cast<T>('\xFE');

    return data.size() > 1 && data[0] == char_0 && data[1] == char_1;
}

template <typename T>
std::string ConvertUtf16toUtf8Conditionally(
    const std::vector<T> &original_data) {
    static_assert(sizeof(T) == 1, "Invalid Data Type in template");

    if (IsVectorMarkedAsUTF16(original_data)) {
        const auto *raw_data =
            reinterpret_cast<const wchar_t *>(original_data.data() + 2);

        std::wstring_view wide_string(
            raw_data, raw_data + (original_data.size() - 2) / 2);
        return wtools::ToUtf8(wide_string);
    }

    std::string data;
    data.assign(original_data.begin(), original_data.end());
    return data;
}

inline void AddSafetyEndingNull(std::string &data) {
    // trick to place in string 0 at the
    // end without changing length
    // this is required for some stupid engines like iostream+YAML
    const auto length = data.size();
    if (data.capacity() <= length) {
        data.reserve(length + 1);
    }
    data[length] = 0;
}

template <typename T>
std::string ConditionallyConvertFromUtf16(const std::vector<T> &original_data) {
    static_assert(sizeof(T) == 1, "Invalid Data Type in template");
    if (original_data.empty()) {
        return {};
    }

    auto d = ConvertUtf16toUtf8Conditionally(original_data);
    AddSafetyEndingNull(d);

    return d;
}

// local implementation of shitty registry access functions
inline uint32_t LocalReadUint32(const char *root_name, const char *name,
                                uint32_t default_value) noexcept {
    HKEY hkey = nullptr;
    auto result = ::RegOpenKeyExA(HKEY_LOCAL_MACHINE, root_name, 0,
                                  KEY_QUERY_VALUE, &hkey);
    if (result != ERROR_SUCCESS) {
        return default_value;
    }

    DWORD value = 0;
    DWORD type = REG_DWORD;
    DWORD size = sizeof(DWORD);
    result = ::RegQueryValueExA(hkey, name, nullptr, &type,
                                reinterpret_cast<PBYTE>(&value), &size);
    ::RegCloseKey(hkey);

    return result == ERROR_SUCCESS ? value : default_value;
}

void InitWindowsCom();
void CloseWindowsCom();
bool IsWindowsComInitialized();
bool InitWindowsComSecurity();

// Low Level Utilities to access and convert VARIANT
inline int32_t WmiGetInt32(const VARIANT &var) noexcept {
    switch (var.vt) {
            // 8 bits values
        case VT_UI1:
            return static_cast<int32_t>(var.bVal);
        case VT_I1:
            return static_cast<int32_t>(var.cVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<int32_t>(var.uiVal);
        case VT_I2:
            return static_cast<int32_t>(var.iVal);
            // 32 bits values
        case VT_UI4:
            return static_cast<int32_t>(var.uintVal);
        case VT_I4:
            return var.intVal;  // no conversion here, we expect good type here
        default:
            return 0;
    }
}

inline uint32_t WmiGetUint32(const VARIANT &var) noexcept {
    switch (var.vt) {
            // 8 bits values
        case VT_UI1:
            return static_cast<uint32_t>(var.bVal);
        case VT_I1:
            return static_cast<uint32_t>(var.cVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<uint32_t>(var.uiVal);
        case VT_I2:
            return static_cast<uint32_t>(var.iVal);
            // 32 bits values
        case VT_UI4:  // no conversion here, we expect good type here
        case VT_I4:
            return var.uintVal;
        default:
            return 0;
    }
}

// Low Level Utilities to access and convert VARIANT
// Tries to get positive numbers instead of negative
inline int64_t WmiGetInt64_KillNegatives(const VARIANT &var) noexcept {
    switch (var.vt) {
        // dumb method to make negative values sometimes positive
        // source: LWA
        // #TODO FIX THIS AS IN MSDN. This is annoying and cumbersome task
        // Microsoft provides us invalid info about data fields
        case VT_I1:
            return var.iVal;
        case VT_I2:
            return var.intVal & 0xFFFF;
        case VT_I4:
            return var.llVal & 0xFFFF'FFFF;  // we have seen 0x00DD'0000'0000

            // 8 bits values
        case VT_UI1:
            return static_cast<int64_t>(var.bVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<int64_t>(var.uiVal);
            // 64 bits values
        case VT_UI4:
            return static_cast<int64_t>(var.uintVal);
        case VT_UI8:
            return static_cast<int64_t>(var.ullVal);
        case VT_I8:
            return var.llVal;  // no conversion here, we expect good type here
        default:
            return 0;
    }
}

// Low Level Utilities to access and convert VARIANT
inline int64_t WmiGetInt64(const VARIANT &var) noexcept {
    switch (var.vt) {
            // 8 bits values
        case VT_UI1:
            return static_cast<int64_t>(var.bVal);
        case VT_I1:
            return static_cast<int64_t>(var.cVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<int64_t>(var.uiVal);
        case VT_I2:
            return static_cast<int64_t>(var.iVal);
            // 64 bits values
        case VT_UI4:
            return static_cast<int64_t>(var.uintVal);
        case VT_I4:
            return static_cast<int64_t>(var.intVal);
        case VT_UI8:
            return static_cast<int64_t>(var.ullVal);
        case VT_I8:
            return var.llVal;  // no conversion here, we expect good type here
        default:
            return 0;
    }
}

inline uint64_t WmiGetUint64(const VARIANT &var) noexcept {
    switch (var.vt) {
            // 8 bits values
        case VT_UI1:
            return static_cast<uint64_t>(var.bVal);
        case VT_I1:
            return static_cast<uint64_t>(var.cVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<uint64_t>(var.uiVal);
        case VT_I2:
            return static_cast<uint64_t>(var.iVal);
        case VT_UI4:
        case VT_I4:
            return static_cast<uint64_t>(var.uintVal);
        case VT_UI8:
            return var.ullVal;  // no conversion here, we expect good type here
        case VT_I8:
            return static_cast<uint64_t>(var.llVal);
        default:
            return 0;
    }
}

bool WmiObjectContains(IWbemClassObject *object, const std::wstring &name);

std::wstring WmiGetWstring(const VARIANT &var);
std::optional<std::wstring> WmiTryGetString(IWbemClassObject *object,
                                            const std::wstring &name);
std::wstring WmiStringFromObject(IWbemClassObject *object,
                                 const std::vector<std::wstring> &names,
                                 std::wstring_view separator);
std::wstring WmiStringFromObject(IWbemClassObject *object,
                                 const std::wstring &name);
std::vector<std::wstring> WmiGetNamesFromObject(IWbemClassObject *wmi_object);

uint64_t WmiUint64FromObject(IWbemClassObject *object,
                             const std::wstring &name);

IEnumWbemClassObject *WmiExecQuery(IWbemServices *services,
                                   const std::wstring &query) noexcept;

/// returned codes from the wmi
enum class WmiStatus { ok, timeout, error, fail_open, fail_connect, bad_param };

std::tuple<IWbemClassObject *, WmiStatus> WmiGetNextObject(
    IEnumWbemClassObject *enumerator, uint32_t timeout);

/// in exception column we have
enum class StatusColumn { ok, timeout };
std::string StatusColumnText(StatusColumn exception_column) noexcept;

/// "decorator" for WMI tables with OK, Timeout: WMIStatus
std::string WmiPostProcess(const std::string &in, StatusColumn status_column,
                           char separator);

// the class is thread safe
class WmiWrapper final {
public:
    WmiWrapper() = default;
    WmiWrapper(const WmiWrapper &) = delete;
    WmiWrapper &operator=(const WmiWrapper &) = delete;
    WmiWrapper(WmiWrapper &&) = delete;
    WmiWrapper &operator=(WmiWrapper &&) = delete;

    ~WmiWrapper() { close(); }
    bool open() noexcept;
    bool connect(std::wstring_view name_space) noexcept;
    // This is OPTIONAL feature, LWA doesn't use it
    [[maybe_unused]] bool impersonate() const noexcept;  // NOLINT
    // on error returns empty string and timeout status
    static std::tuple<std::wstring, WmiStatus> produceTable(
        IEnumWbemClassObject *enumerator,
        const std::vector<std::wstring> &existing_names,
        std::wstring_view separator, uint32_t wmi_timeout) noexcept;

    /// work horse to ask certain names from the target
    /// on error returns empty string and timeout status
    std::tuple<std::wstring, WmiStatus> queryTable(
        const std::vector<std::wstring> &names, const std::wstring &target,
        std::wstring_view separator, uint32_t wmi_timeout) const noexcept;

    /// special purposes: formatting for PS for example
    /// on error returns nullptr
    /// You have to call Release for returned object!!!
    IEnumWbemClassObject *queryEnumerator(
        const std::vector<std::wstring> &names,
        const std::wstring &target) const noexcept;

private:
    void close() noexcept;
    static std::wstring makeQuery(const std::vector<std::wstring> &names,
                                  const std::wstring &target) noexcept;

    mutable std::mutex lock_;
    IWbemLocator *locator_{nullptr};
    IWbemServices *services_{nullptr};
};

HMODULE LoadWindowsLibrary(const std::wstring &dll_path);

/// Look into the registry in order to find out, which
/// event logs are available
/// return false only when something wrong with registry
std::vector<std::string> EnumerateAllRegistryKeys(const char *reg_path);

/// returns data from the root machine registry
uint32_t GetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                          uint32_t dflt) noexcept;
bool DeleteRegistryValue(std::wstring_view path,
                         std::wstring_view value_name) noexcept;
bool SetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                      std::wstring_view value) noexcept;

bool SetRegistryValueExpand(std::wstring_view path,
                            std::wstring_view value_name,
                            std::wstring_view value);
bool SetRegistryValue(std::wstring_view path, std::wstring_view value_name,
                      uint32_t value) noexcept;
std::wstring GetRegistryValue(std::wstring_view path,
                              std::wstring_view value_name,
                              std::wstring_view dflt) noexcept;
std::wstring GetArgv(uint32_t index) noexcept;
size_t GetCommitCharge(uint32_t pid) noexcept;
size_t GetOwnVirtualSize() noexcept;

namespace monitor {
constexpr size_t kMaxMemoryAllowed = 200'000'000;
bool IsAgentHealthy() noexcept;
}  // namespace monitor

class ACLInfo final {
public:
    struct AceList {
        ACE_HEADER *ace;
        BOOL allowed;
        AceList *next;
    };
    /// \b bstrPath - path for which ACL info should be queried
    explicit ACLInfo(const _bstr_t &path) noexcept;
    ACLInfo(const ACLInfo &) = delete;
    ACLInfo operator=(const ACLInfo &) = delete;
    ACLInfo(ACLInfo &&) = delete;
    ACLInfo operator=(ACLInfo &&) = delete;
    ~ACLInfo();
    /// \b Queries NTFS for ACL Info of the file/directory
    HRESULT query() noexcept;
    /// \b Outputs ACL info in Human-readable format
    [[nodiscard]] std::string output() const;

private:
    void clearAceList() noexcept;
    HRESULT addAceToList(ACE_HEADER *ace) noexcept;
    _bstr_t path_;
    AceList *ace_list_;  // list of Access Control Entries
};

std::string ReadWholeFile(const std::filesystem::path &fname) noexcept;

bool PatchFileLineEnding(const std::filesystem::path &fname) noexcept;

using InternalUser = std::pair<std::wstring, std::wstring>;  // name, password

class InternalUsersDb {
public:
    InternalUsersDb() = default;
    InternalUsersDb(const InternalUsersDb &) = delete;
    InternalUsersDb(InternalUsersDb &&) = delete;
    InternalUsersDb &operator=(const InternalUsersDb &) = delete;
    InternalUsersDb &operator=(InternalUsersDb &&) = delete;
    ~InternalUsersDb() { killAll(); }
    InternalUser obtainUser(std::wstring_view group);
    void killAll();
    size_t size() const;

private:
    mutable std::mutex users_lock_;
    std::unordered_map<std::wstring, wtools::InternalUser> users_;
};

InternalUser CreateCmaUserInGroup(const std::wstring &group_name) noexcept;
InternalUser CreateCmaUserInGroup(const std::wstring &group_name,
                                  std::wstring_view prefix) noexcept;
bool RemoveCmaUser(const std::wstring &user_name) noexcept;
std::wstring GenerateRandomString(size_t max_length) noexcept;
std::wstring GenerateCmaUserNameInGroup(std::wstring_view group) noexcept;
std::wstring GenerateCmaUserNameInGroup(std::wstring_view group,
                                        std::wstring_view prefix) noexcept;

class Bstr {
public:
    Bstr(const Bstr &) = delete;
    Bstr(Bstr &&) = delete;
    Bstr &operator=(const Bstr &) = delete;
    Bstr &operator=(Bstr &&) = delete;

    explicit Bstr(std::wstring_view str) noexcept
        : data_{::SysAllocString(str.data())} {}
    ~Bstr() { ::SysFreeString(data_); }
    [[nodiscard]] BSTR bstr() const noexcept { return data_; }

private:
    BSTR data_;
};

/// Add command to set correct access rights for the path
void ProtectPathFromUserWrite(const std::filesystem::path &path,
                              std::vector<std::wstring> &commands);

/// Add command to remove user write to the path
void ProtectFileFromUserWrite(const std::filesystem::path &path,
                              std::vector<std::wstring> &commands);

/// Add command to remove user access to the path
void ProtectPathFromUserAccess(const std::filesystem::path &entry,
                               std::vector<std::wstring> &commands);

enum class ExecuteMode { sync, async };

/// Create cmd file in %Temp% and run it.
///
/// Returns script name path to be executed
std::filesystem::path ExecuteCommands(std::wstring_view name,
                                      const std::vector<std::wstring> &commands,
                                      ExecuteMode mode);

/// Create folder in %Temp% and set only owner permissions
///
/// Returns path
std::optional<std::filesystem::path> MakeSafeTempFolder(
    std::string_view sub_dir);

/// Changes Access Rights in Windows crazy manner
///
///
bool ChangeAccessRights(
    const wchar_t *object_name,   // name of object
    SE_OBJECT_TYPE object_type,   // type of object
    const wchar_t *trustee_name,  // trustee for new ACE
    TRUSTEE_FORM trustee_form,    // format of trustee structure
    DWORD access_rights,          // access mask for new ACE
    ACCESS_MODE access_mode,      // type of ACE
    DWORD inheritance             // inheritance flags for new ACE ???
);

inline bool ChangeAccessRights(
    std::filesystem::path file,      // name of file
    std::wstring_view trustee_name,  // user for new ACE
    DWORD access_rights,             // access mask for new ACE
    ACCESS_MODE access_mode,         // type of ACE
    DWORD inheritance                // inheritance flags for new ACE ???
) {
    return ChangeAccessRights(file.wstring().c_str(), SE_FILE_OBJECT,
                              trustee_name.data(), TRUSTEE_IS_NAME,
                              access_rights, access_mode, inheritance);
}

std::wstring ExpandStringWithEnvironment(std::wstring_view str);

const wchar_t *GetMultiSzEntry(wchar_t *&pos, const wchar_t *end);

std::wstring SidToName(std::wstring_view sid, const SID_NAME_USE &sid_type);

std::vector<char> ReadFromHandle(HANDLE handle);

/// Calls any command and return back output
///
/// Wraps AppRunner
std::string RunCommand(std::wstring_view cmd);

/// Validates pid is connected to the port
bool CheckProcessUsePort(uint16_t port, uint32_t pid, uint16_t peer_port);

/// Finds a pid of process working with connection
std::optional<uint32_t> GetConnectionPid(uint16_t port, uint16_t peer_port);

uint32_t GetServiceStatus(const std::wstring &name) noexcept;

struct AdapterInfo {
    std::string guid;
    std::wstring friendly_name;
    std::wstring description;
    IFTYPE if_type;
    std::optional<uint64_t> receive_speed;
    std::optional<uint64_t> transmit_speed;
    IF_OPER_STATUS oper_status;
    std::string mac_address;
};
using AdapterInfoStore = std::unordered_map<std::wstring, AdapterInfo>;

AdapterInfoStore GetAdapterInfoStore();

//// Mangles names for use as a counter names
/// See: MSDN, PerformanceCounter.InstanceName Property
/// https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.performancecounter.instancename?view=dotnet-plat-ext-8.0
std::wstring MangleNameForPerfCounter(std::wstring_view name) noexcept;

////
//// Helper functions for service providers
////

std::string ReplaceBlankLineWithSeparator(std::string const &raw,
                                          std::string_view separator);

struct OsInfo {
    std::wstring name;
    std::wstring version;
};

std::optional<OsInfo> GetOsInfo();

std::optional<std::tm> GetTimeAsTm(
    std::chrono::system_clock::time_point time_point);
std::optional<std::wstring> FindUserName(const PSID sid);
}  // namespace wtools

#endif  // WTOOLS_H
