// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// wtools.h
//
// Windows Specific Tools
//
#pragma once

#ifndef wtools_h__
#define wtools_h__
#if defined(_WIN32)
#include <aclapi.h>
#include <comdef.h>

#include "windows.h"
#include "winperf.h"

#define _WIN32_DCOM

#include <Wbemidl.h>
#include <tlhelp32.h>
#endif

#include <atomic>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <tuple>

#include "datablock.h"
#include "tools/_process.h"
#include "tools/_tgt.h"
#include "tools/_win.h"
#include "tools/_xlog.h"

namespace wtools {
constexpr const wchar_t *kWToolsLogName = L"check_mk_wtools.log";

inline void *ProcessHeapAlloc(size_t size) {
    return ::HeapAlloc(::GetProcessHeap(), HEAP_ZERO_MEMORY, size);
}

inline void ProcessHeapFree(void *data) {
    if (data != nullptr) {
        ::HeapFree(::GetProcessHeap(), 0, data);
    }
}

enum class SecurityLevel { standard, admin };

// RAII class to keep MS Windows Security Descriptor temporary
class SecurityAttributeKeeper {
public:
    SecurityAttributeKeeper(SecurityLevel sl);
    ~SecurityAttributeKeeper();

    const SECURITY_ATTRIBUTES *get() const { return sa_; }
    SECURITY_ATTRIBUTES *get() { return sa_; }

private:
    bool allocAll(SecurityLevel sl);
    void cleanupAll();
    // below are allocated using ProcessHeapAlloc values
    SECURITY_DESCRIPTOR *sd_{nullptr};
    SECURITY_ATTRIBUTES *sa_{nullptr};
    ACL *acl_{nullptr};
};

// this is functor to kill any pointer allocated with ::LocalAlloc
// usually this pointer comes from Windows API
template <typename T>
struct LocalAllocDeleter {
    void operator()(T *r) noexcept {
        if (r != nullptr) ::LocalFree(reinterpret_cast<HLOCAL>(r));
    }
};

// usage
#if (0)
LocalResource<SERVICE_FAILURE_ACTIONS> actions(
    ::WindowsApiToGetActions(handle_to_service));
#endif
//
template <typename T>
using LocalResource = std::unique_ptr<T, LocalAllocDeleter<T>>;

struct HandleDeleter {
    using pointer = HANDLE;  // trick to use HANDLE as STL pointer
    void operator()(HANDLE h) { ::CloseHandle(h); }
};

/// Unique ptr for Windows HANDLE
using UniqueHandle = std::unique_ptr<HANDLE, HandleDeleter>;

// returns <exit_code, 0>, <0, error> or <-1, error>
std::pair<uint32_t, uint32_t> GetProcessExitCode(uint32_t pid);

[[nodiscard]] std::wstring GetProcessPath(uint32_t pid) noexcept;

[[nodiscard]] int KillProcessesByDir(const std::filesystem::path &dir) noexcept;

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
bool UninstallService(
    const wchar_t *service_name,
    UninstallServiceMode uninstall_mode = UninstallServiceMode::normal);

// Abstract Interface template for SERVICE PROCESSOR:
// WE ARE NOT GOING TO USE AT ALL.
// One binary - one object of one class
// This is just to check validness during initial development
class BaseServiceProcessor {
public:
    virtual ~BaseServiceProcessor() = default;
    // Standard Windows API to Service hit here
    virtual void stopService() = 0;
    virtual void startService() = 0;
    virtual void pauseService() = 0;
    virtual void continueService() = 0;
    virtual void shutdownService() = 0;
    virtual const wchar_t *getMainLogName() const = 0;
    virtual void cleanupOnStop() {}
};

// keeps two handles
class SimplePipe {
public:
    SimplePipe() : read_(nullptr), write_(nullptr), sa_initialized_(false) {
        sa_.lpSecurityDescriptor = &sd_;
        sa_.nLength = sizeof(SECURITY_ATTRIBUTES);

        sa_.bInheritHandle = TRUE;  // allow handle inherit for child process
    }

    SimplePipe(const SimplePipe &) = delete;
    SimplePipe &operator=(const SimplePipe &) = delete;
    SimplePipe(SimplePipe &&Rhs) = delete;
    SimplePipe &operator=(SimplePipe &&Rhs) = delete;

    ~SimplePipe() { shutdown(); }

    bool create() {
        // protected by lock
        std::lock_guard lk(lock_);
        if (read_ || write_) return true;

        if (!sa_initialized_) {
            auto ret = initDescriptorsWithFullAccess();
            if (!ret) return false;  // really, something weird
        }

        if (!::CreatePipe(&read_, &write_, &sa_, 0)) {
            read_ = nullptr;
            write_ = nullptr;
            xlog::l("Failed to create pipe, %d", GetLastError()).print();
            return false;
        }

        // disable inheriting from the child
        if (!SetHandleInformation(read_, HANDLE_FLAG_INHERIT, 0)) {
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

    void shutdown() {
        std::lock_guard lk(lock_);
        if (read_) {
            CloseHandle(read_);
            xlog::v("Closed read %p", read_);
            read_ = nullptr;
        }
        if (write_) {
            CloseHandle(write_);
            xlog::v("Closed write %p", write_);
            write_ = nullptr;
        }
    }

    const HANDLE getRead() const noexcept {
        std::lock_guard lk(lock_);
        return read_;
    }
    const HANDLE getWrite() const noexcept {
        std::lock_guard lk(lock_);
        return write_;
    }

    const HANDLE moveWrite() noexcept {
        std::lock_guard lk(lock_);
        auto write = write_;
        write_ = nullptr;
        return write;
    }

private:
    bool initDescriptorsWithFullAccess() {
        auto ret =
            ::InitializeSecurityDescriptor(&sd_, SECURITY_DESCRIPTOR_REVISION);
        if (!ret) {
            xlog::l(XLOG_FLINE + "Stupid fail").print();
            return false;
        }

        // *******************************************************
        // #TODO change access right to the owner of the process
        // below we have code from the winagent, which grants any access to
        // the object this is quite dangerous
        // NOW THIS IS BY DESIGN of Check MK
        // https://docs.microsoft.com/de-at/windows/desktop/SecAuthZ/creating-a-security-descriptor-for-a-new-object-in-c--
        // ******************************************************
        ret = ::SetSecurityDescriptorDacl(&sd_, true, nullptr, false);
        if (!ret) {
            xlog::l(XLOG_FLINE + "Not so stupid fail %d", GetLastError())
                .print();
            return false;
        }
        sa_initialized_ = true;
        return true;
    }
    mutable std::mutex lock_;
    HANDLE read_;
    HANDLE write_;
    bool sa_initialized_;
    SECURITY_DESCRIPTOR sd_ = {0};
    SECURITY_ATTRIBUTES sa_;
};

// scans all processes in system and calls op
// returns false only when something is really bad
// based on ToolHelp api family
// normally require elevation
// if op returns false, scan will be stopped(this is only optimization)
bool ScanProcessList(const std::function<bool(const PROCESSENTRY32 &)> &op);

// standard process terminator
bool KillProcess(uint32_t pid, int exit_code) noexcept;

// process terminator
// used to kill OpenHardwareMonitor
bool KillProcess(std::wstring_view process_name, int exit_code = 9) noexcept;

// special function to kill suspicious processes with all here children
// useful mostly to stop legacy agent which may have plugins running
bool KillProcessFully(const std::wstring &process_name,
                      int exit_code = 9) noexcept;

// calculates count of processes in the system
int FindProcess(std::wstring_view process_name) noexcept;

constexpr bool kProcessTreeKillAllowed = false;

// WIN32 described method of killing process tree
void KillProcessTree(uint32_t ProcessId);

class AppRunner {
public:
    AppRunner()
        : process_id_(0)
        , exit_code_(STILL_ACTIVE)
        , job_handle_(nullptr)
        , process_handle_(nullptr) {}

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

    // returns process id
    uint32_t goExecAsJobAndUser(std::wstring_view user,
                                std::wstring_view password,
                                std::wstring_view command_line) noexcept;
    // returns process id
    uint32_t goExecAsDetached(std::wstring_view command_line) noexcept;

    void kill(bool kill_tree_too) {
        auto proc_id = process_id_.exchange(0);
        if (proc_id == 0) {
            xlog::v(
                "Attempt to kill process which is not started or already killed");
            return;
        }

        if (kill_tree_too) {
            if (job_handle_) {
                // this is normal case but with job
                TerminateJobObject(job_handle_, 0);

                // job:
                CloseHandle(job_handle_);
                job_handle_ = nullptr;

                // process:
                CloseHandle(process_handle_);  // must
                process_handle_ = nullptr;
            } else {
                if (kProcessTreeKillAllowed) KillProcessTree(proc_id);
            }

            return;
        }

        if (exit_code_ == STILL_ACTIVE) {
            auto success = KillProcess(proc_id, -1);
            if (!success)
                xlog::v("Failed kill {} status {}", proc_id, GetLastError());
        }
    }

    const auto getCmdLine() const { return cmd_line_; }
    const auto processId() const { return process_id_.load(); }
    const auto exitCode() const { return exit_code_; }
    const auto getStdioRead() const { return stdio_.getRead(); }
    const auto getStderrRead() const { return stderr_.getRead(); }

    const auto &getData() const { return data_; }

    auto &getData() { return data_; }
    bool trySetExitCode(uint32_t Pid, uint32_t Code) {
        if (Pid && Pid == process_id_) {
            exit_code_ = Code;
            return true;
        }
        return false;
    }

private:
    void prepareResources(std::wstring_view command_line,
                          bool create_pipe) noexcept;
    void cleanResources() noexcept;
    void setExitCode(uint32_t Code) { exit_code_ = Code; }
    std::wstring cmd_line_;
    std::atomic<uint32_t> process_id_;
    HANDLE job_handle_;
    HANDLE process_handle_;
    SimplePipe stdio_;
    SimplePipe stderr_;

    // output
    std::vector<char> data_;
    uint32_t exit_code_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class Wtools;
    FRIEND_TEST(Wtools, AppRunner);
#endif
};

class ServiceController {
private:
    static std::mutex s_lock_;
    static ServiceController *s_controller_;  // probably we need her shared
                                              // ptr, but this is clear overkill
public:
    ServiceController(std::unique_ptr<wtools::BaseServiceProcessor> processor);

    ServiceController(const ServiceController &) = delete;
    ServiceController &operator=(const ServiceController &) = delete;
    ServiceController(ServiceController &&) = delete;
    ServiceController &operator=(ServiceController &&) = delete;

    ~ServiceController() {
        std::lock_guard lk(s_lock_);
        if (s_controller_ && s_controller_ == this) {
            s_controller_ = nullptr;
        }
    }

    // no return from here till service ends
    enum class StopType { normal, no_connect, fail };
    StopType registerAndRun(const wchar_t *service_name, bool can_stop = true,
                            bool can_shutdown = true,
                            bool can_pause_continue = true);

protected:
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
    void setServiceStatus(DWORD current_state, DWORD win32_exit_code = NO_ERROR,
                          DWORD wait_hint = 0) {
        static DWORD check_point = 1;

        // Fill in the SERVICE_STATUS structure of the service.
        status_.dwCurrentState = current_state;
        status_.dwWin32ExitCode = win32_exit_code;
        status_.dwWaitHint = wait_hint;

        status_.dwCheckPoint = ((current_state == SERVICE_RUNNING) ||
                                (current_state == SERVICE_STOPPED))
                                   ? 0
                                   : check_point++;

        // Report the status of the service to the SCM.
        auto ret = ::SetServiceStatus(status_handle_, &status_);
        xlog::l("Setting state %d result %d", current_state,
                ret ? 0 : GetLastError())
            .print();
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
    const wchar_t *log_name_ = wtools::kWToolsLogName;

    std::unique_ptr<wchar_t[]> name_;
    bool can_stop_;
    bool can_shutdown_;
    bool can_pause_continue_;

    SERVICE_STATUS status_;
    SERVICE_STATUS_HANDLE status_handle_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ServiceControllerTest;
    FRIEND_TEST(ServiceControllerTest, CreateDelete);
    FRIEND_TEST(ServiceControllerTest, StartStop);
#endif
};

// Standard converter, generates no exception in Windows
// we support two converters
// one is deprecated, second is windows only
inline std::string ToUtf8(const std::wstring_view src) noexcept {
#if defined(WINDOWS_OS)
    // Windows only
    auto in_len = static_cast<int>(src.length());
    auto out_len =
        ::WideCharToMultiByte(CP_UTF8, 0, src.data(), in_len, NULL, 0, 0, 0);
    if (out_len == 0) return {};

    std::string str;
    try {
        str.resize(out_len);
    } catch (const std::exception &e) {
        xlog::l(XLOG_FUNC + "memory lacks %s", e.what());
        return {};
    }

    // convert
    ::WideCharToMultiByte(CP_UTF8, 0, src.data(), -1, str.data(), out_len, 0,
                          0);
    return str;
#else
    // standard but deprecated
    try {
        return wstring_convert<codecvt_utf8<wchar_t>>().to_bytes(src);
    } catch (const exception &e) {
        xlog::l("Failed to convert %ls", src.c_str());
        return "";
    }
#endif  // endif
}

inline std::string ToUtf8(std::string_view src) noexcept {
    return std::string(src);
}

std::wstring ToCanonical(std::wstring_view raw_app_name);
// standard Windows converter from Microsoft
// WINDOWS ONLY
inline std::wstring ConvertToUTF16(std::string_view src) noexcept {
#if defined(WINDOWS_OS)
    auto in_len = static_cast<int>(src.length());
    auto utf8_str = src.data();
    auto out_len = MultiByteToWideChar(CP_UTF8, 0, utf8_str, in_len, NULL, 0);
    std::wstring wstr;
    try {
        wstr.resize(out_len);
    } catch (const std::exception &e) {
        xlog::l("memory lacks %s", e.what());
        return {};
    }

    if (MultiByteToWideChar(CP_UTF8, 0, utf8_str, in_len, wstr.data(),
                            out_len) == out_len) {
        return wstr;
    }
    return {};
#else
    xlog::l(XLOG_FUNC + ": UR crazy");
    return {};
#endif
}

namespace perf {

using NameMap = std::unordered_map<unsigned long, std::wstring>;

// read MULTI_SZ string from the registry
enum class PerfCounterReg { national, english };
std::vector<wchar_t> ReadPerfCounterKeyFromRegistry(PerfCounterReg type);
std::optional<uint32_t> FindPerfIndexInRegistry(std::wstring_view key);
NameMap GenerateNameMap();

// ************************
// #TODO probably we need a class wrapper here
// ************************
// to simplify reading
using DataSequence = cma::tools::DataBlock<BYTE>;

// API:
// 1. Read data from registry
DataSequence ReadPerformanceDataFromRegistry(
    const std::wstring &counter_list) noexcept;

// 2. Find required object
const PERF_OBJECT_TYPE *FindPerfObject(const DataSequence &data_sequence,
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
                                               const NameMap &map);
// 5. And Values!
std::vector<ULONGLONG> GenerateValues(
    const PERF_COUNTER_DEFINITION &counter,
    std::vector<const PERF_INSTANCE_DEFINITION *> &instances) noexcept;

uint64_t GetValueFromBlock(const PERF_COUNTER_DEFINITION &counter,
                           const PERF_COUNTER_BLOCK *block) noexcept;

std::string GetName(uint32_t counter_type) noexcept;
}  // namespace perf

inline int64_t QueryPerformanceFreq() noexcept {
    LARGE_INTEGER frequency;
    ::QueryPerformanceFrequency(&frequency);
    return frequency.QuadPart;
}

inline int64_t QueryPerformanceCo() {
    LARGE_INTEGER counter;
    ::QueryPerformanceCounter(&counter);
    return counter.QuadPart;
}

// util to get in windows find path to your binary
// MAY NOT WORK when you are running as a service
std::filesystem::path GetCurrentExePath();

// wrapper for win32 specific function
// return 0 when no data or error
inline int DataCountOnHandle(HANDLE handle) {
    DWORD read_count = 0;

    // MSDN says to do so
    auto peek_result =
        ::PeekNamedPipe(handle, nullptr, 0, nullptr, &read_count, nullptr);

    if (0 == peek_result) {
        return 0;
    }

    return read_count;
}

template <typename T>
bool IsVectorMarkedAsUTF16(const std::vector<T> &data) {
    static_assert(sizeof(T) == 1, "Invalid Data Type in template");
    constexpr T char_0 = static_cast<T>('\xFF');
    constexpr T char_1 = static_cast<T>('\xFE');

    return data.size() > 1 && data[0] == char_0 && data[1] == char_1;
}

template <typename T>
std::string SmartConvertUtf16toUtf8(const std::vector<T> &original_data) {
    static_assert(sizeof(T) == 1, "Invalid Data Type in template");
    bool convert_required = IsVectorMarkedAsUTF16(original_data);

    if (convert_required) {
        auto raw_data =
            reinterpret_cast<const wchar_t *>(original_data.data() + 2);

        std::wstring wdata(raw_data, raw_data + (original_data.size() - 2) / 2);
        if (wdata.empty()) return {};

        return wtools::ToUtf8(wdata);
    }

    std::string data;
    data.assign(original_data.begin(), original_data.end());
    return data;
}

inline void AddSafetyEndingNull(std::string &data) {
    // trick to place in string 0 at the
    // end without changing length
    // this is required for some stupid engines like iostream+YAML
    auto length = data.size();
    if (data.capacity() <= length) data.reserve(length + 1);
    data[length] = 0;
}

// templated to support uint8_t and int8_t and char and unsigned char
template <typename T>
std::string ConditionallyConvertFromUTF16(const std::vector<T> &original_data) {
    static_assert(sizeof(T) == 1, "Invalid Data Type in template");
    if (original_data.empty()) {
        return {};
    }

    auto d = SmartConvertUtf16toUtf8(original_data);
    AddSafetyEndingNull(d);

    return d;
}

// local implementation of shitty registry access functions
inline uint32_t LocalReadUint32(const char *root_name, const char *name,
                                uint32_t default_value = 0) noexcept {
    HKEY hkey = nullptr;
    auto result = ::RegOpenKeyExA(HKEY_LOCAL_MACHINE, root_name, 0,
                                  KEY_QUERY_VALUE, &hkey);
    if (result != ERROR_SUCCESS) {
        return default_value;
    }

    DWORD value = 0;
    DWORD type = REG_DWORD;
    DWORD size = sizeof(DWORD);
    result =
        ::RegQueryValueExA(hkey, name, nullptr, &type, (PBYTE)&value, &size);
    ::RegCloseKey(hkey);

    if (result == ERROR_SUCCESS) {
        return value;
    }

    return default_value;
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
        case VT_UI4:
            return var.uintVal;  // no conversion here, we expect good type here
        case VT_I4:
            return static_cast<uint32_t>(var.uintVal);
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
            return static_cast<uint64_t>(var.uintVal);
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

std::wstring WmiGetWstring(const VARIANT &Var);
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

// returned codes from the wmi
enum class WmiStatus { ok, timeout, error, fail_open, fail_connect, bad_param };

std::tuple<IWbemClassObject *, WmiStatus> WmiGetNextObject(
    IEnumWbemClassObject *enumerator, uint32_t timeout);

// in exception column we have
enum class StatusColumn { ok, timeout };
std::string StatusColumnText(StatusColumn exception_column) noexcept;

// "decorator" for WMI tables with OK, Timeout: WMIStatus
std::string WmiPostProcess(const std::string &in, StatusColumn exception_column,
                           char separator);

// the class is thread safe
class WmiWrapper {
public:
    WmiWrapper() : locator_(nullptr), services_(nullptr) {}

    WmiWrapper(const WmiWrapper &) = delete;
    WmiWrapper &operator=(const WmiWrapper &) = delete;
    WmiWrapper(WmiWrapper &&) = delete;
    WmiWrapper &operator=(WmiWrapper &&) = delete;

    virtual ~WmiWrapper() { close(); }
    bool open() noexcept;
    bool connect(std::wstring_view name_space) noexcept;
    // This is OPTIONAL feature, LWA doesn't use it
    bool impersonate() noexcept;
    // on error returns empty string and timeout status
    static std::tuple<std::wstring, WmiStatus> produceTable(
        IEnumWbemClassObject *enumerator,
        const std::vector<std::wstring> &names, std::wstring_view separator,
        uint32_t wmi_timeout) noexcept;

    // work horse to ask certain names from the target
    // on error returns empty string and timeout status
    std::tuple<std::wstring, WmiStatus> queryTable(
        const std::vector<std::wstring> &names, const std::wstring &target,
        std::wstring_view separator, uint32_t wmi_timeout) noexcept;

    // special purposes: formatting for PS for example
    // on error returns nullptr
    // You have to call Release for returned object!!!
    IEnumWbemClassObject *queryEnumerator(
        const std::vector<std::wstring> &names,
        const std::wstring &target) noexcept;

private:
    void close() noexcept;
    static std::wstring makeQuery(const std::vector<std::wstring> &Names,
                                  const std::wstring &Target) noexcept;

    mutable std::mutex lock_;
    IWbemLocator *locator_;
    IWbemServices *services_;
};

HMODULE LoadWindowsLibrary(const std::wstring &DllPath);

// Look into the registry in order to find out, which
// event logs are available
// return false only when something wrong with registry
std::vector<std::string> EnumerateAllRegistryKeys(const char *RegPath);

// returns data from the root machine registry
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
size_t GetOwnVirtualSize() noexcept;

namespace monitor {
constexpr size_t kMaxMemoryAllowed = 200'000'000;
bool IsAgentHealthy() noexcept;
}  // namespace monitor

class ACLInfo {
public:
    struct AceList {
        ACE_HEADER *ace;
        BOOL allowed;
        AceList *next;
    };
    /// \b bstrPath - path for which ACL info should be queried
    ACLInfo(const _bstr_t &path) noexcept;
    virtual ~ACLInfo();
    /// \b Queries NTFS for ACL Info of the file/directory
    HRESULT query() noexcept;
    /// \b Outputs ACL info in Human-readable format
    std::string output();

private:
    void clearAceList() noexcept;
    HRESULT addAceToList(ACE_HEADER *pAce) noexcept;

private:
    _bstr_t path_;
    AceList *ace_list_;  // list of Access Control Entries
};

std::string ReadWholeFile(const std::filesystem::path &fname) noexcept;

bool PatchFileLineEnding(const std::filesystem::path &fname) noexcept;

using InternalUser = std::pair<std::wstring, std::wstring>;  // name,pwd

InternalUser CreateCmaUserInGroup(const std::wstring &group_name) noexcept;
bool RemoveCmaUser(const std::wstring &user_name) noexcept;
std::wstring GenerateRandomString(size_t max_length) noexcept;
std::wstring GenerateCmaUserNameInGroup(std::wstring_view group) noexcept;

class Bstr {
public:
    Bstr(const Bstr &) = delete;
    Bstr(Bstr &&) = delete;
    Bstr &operator=(const Bstr &) = delete;
    Bstr &operator=(Bstr &&) = delete;

    Bstr(std::wstring_view str) { data_ = ::SysAllocString(str.data()); }
    ~Bstr() { ::SysFreeString(data_); }
    operator BSTR() { return data_; }

public:
    BSTR data_;
};

/// \brief Add command to set correct access rights for the path
void ProtectPathFromUserWrite(const std::filesystem::path &path,
                              std::vector<std::wstring> &commands);

/// \brief Add command to remove user write to the path
void ProtectFileFromUserWrite(const std::filesystem::path &path,
                              std::vector<std::wstring> &commands);

/// \brief Add command to remove user access to the path
void ProtectPathFromUserAccess(const std::filesystem::path &entry,
                               std::vector<std::wstring> &commands);

/// \brief Create cmd file in %Temp% and run it.
///
/// Returns script name path to be executed
std::filesystem::path ExecuteCommandsAsync(
    std::wstring_view name, const std::vector<std::wstring> &commands);

/// \brief Create cmd file in %Temp% and run it.
///
/// Returns script name path to be executed
std::filesystem::path ExecuteCommandsSync(
    std::wstring_view name, const std::vector<std::wstring> &commands);

/// \brief Changes Access Rights in Windows crazy manner
///
/// Example of usage is
/// ChangeAccessRights( L"c:\\txt", SE_FILE_OBJECT,        // what
///                     L"a1", TRUSTEE_IS_NAME,            // who
///                     STANDARD_RIGHTS_ALL | GENERIC_ALL, // how
///                     GRANT_ACCESS, OBJECT_INHERIT_ACE);
bool ChangeAccessRights(
    const wchar_t *object_name,   // name of object
    SE_OBJECT_TYPE object_type,   // type of object
    const wchar_t *trustee_name,  // trustee for new ACE
    TRUSTEE_FORM trustee_form,    // format of trustee structure
    DWORD access_rights,          // access mask for new ACE
    ACCESS_MODE access_mode,      // type of ACE
    DWORD inheritance             // inheritance flags for new ACE ???
);

std::wstring ExpandStringWithEnvironment(std::wstring_view str);

const wchar_t *GetMultiSzEntry(wchar_t *&pos, const wchar_t *end);

std::wstring SidToName(const std::wstring_view sid,
                       const SID_NAME_USE &sid_type);

std::vector<char> ReadFromHandle(HANDLE handle);

/// \brief Calls any command and return back output
///
/// Wraps AppRunner
std::string RunCommand(std::wstring_view cmd);

/// Validates pid is connected to the port<summary>
bool CheckProcessUsePort(uint16_t port, uint32_t pid, uint16_t peer_port);

}  // namespace wtools

#endif  // wtools_h__
