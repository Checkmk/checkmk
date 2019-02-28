// wtools.h
//
// Windows Specific Tools
//
#pragma once

#ifndef wtools_h__
#define wtools_h__
#define WIN32_LEAN_AND_MEAN
#include "windows.h"
#include "winperf.h"

#define _WIN32_DCOM

#include <Wbemidl.h>
#include <comdef.h>

#include <shellapi.h>
#include <tlhelp32.h>

#include <assert.h>

#include <atomic>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>

#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"
#include "tools/_xlog.h"

#include "datablock.h"

namespace wtools {
constexpr const wchar_t* kWToolsLogName = L"check_mk_wtools.log";

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
                    uint32_t dwStartType, const wchar_t* Dependencies,
                    const wchar_t* Account, const wchar_t* Password);
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
bool UninstallService(const wchar_t* ServiceName);

// Abstract Interface template for SERVICE PROCESSOR:
// WE ARE NOT GOING TO USE AT ALL.
// One binary - one object of one class
// This is just to check validness during initial development
class BaseServiceProcessor {
public:
    virtual ~BaseServiceProcessor() {}
    // Standard Windows API to Service hit here
    virtual void stopService() = 0;
    virtual void startService() = 0;
    virtual void pauseService() = 0;
    virtual void continueService() = 0;
    virtual void shutdownService() = 0;
    virtual const wchar_t* getMainLogName() const = 0;
    virtual void preContextCall() = 0;
};

// keeps two handles
class SimplePipe {
public:
    SimplePipe() : read_(0), write_(0), sa_initialized_(false) {
        sa_.lpSecurityDescriptor = &sd_;
        sa_.nLength = sizeof(SECURITY_ATTRIBUTES);

        sa_.bInheritHandle = true;  // allow handle inherit for child process
    }

    SimplePipe(const SimplePipe&) = delete;
    SimplePipe& operator=(const SimplePipe&) = delete;

    // #TODO Should be provided
    SimplePipe(SimplePipe&& Rhs) = delete;
    // #TODO Should be provided
    SimplePipe& operator=(SimplePipe&& Rhs) = delete;

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
            read_ = 0;
            write_ = 0;
            xlog::l("Failed to create pipe, %d", GetLastError()).print();
            return false;
        }

        // disable inheriting from the child
        if (!SetHandleInformation(read_, HANDLE_FLAG_INHERIT, 0)) {
            xlog::l("Failed to change handle information, %d", GetLastError())
                .print();
            ::CloseHandle(read_);
            ::CloseHandle(write_);
            read_ = 0;
            write_ = 0;
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
            read_ = 0;
        }
        if (write_) {
            CloseHandle(write_);
            xlog::v("Closed write %p", write_);
            write_ = 0;
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
        write_ = 0;
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
    SECURITY_DESCRIPTOR sd_;
    SECURITY_ATTRIBUTES sa_;
};

// WIN32 described method of killing process tree
inline void KillProcessTree(uint32_t ProcessId) {
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
            cma::tools::win::KillProcess(process.th32ProcessID);
        }

    } while (Process32Next(snapshot, &process));
}

class AppRunner {
public:
    AppRunner() : process_id_(0), exit_code_(STILL_ACTIVE), job_(nullptr) {}
    ~AppRunner() {
        kill(true);
        stdio_.shutdown();
        stderr_.shutdown();
    }

    // returns process id
    uint32_t goExec(std::wstring CommandLine, bool Wait, bool InheritHandle,
                    bool PipeOutput) noexcept {
        try {
            if (PipeOutput) {
                stdio_.create();
                stderr_.create();
            }
            cmd_line_ = CommandLine;
            job_ = nullptr;
            uint32_t proc_id = 0;
            if (use_job_)
                proc_id = cma::tools::RunStdCommandAsJob(
                    job_, CommandLine.c_str(), InheritHandle, stdio_.getWrite(),
                    stderr_.getWrite());
            else
                proc_id = cma::tools::RunStdCommand(
                    CommandLine.c_str(), Wait, InheritHandle, stdio_.getWrite(),
                    stderr_.getWrite());

            if (proc_id) {
                process_id_ = proc_id;
                return proc_id;
            }

            xlog::l(XLOG_FLINE + " Failed RunStd: %d", GetLastError());

            job_ = nullptr;
            process_id_ = 0;
            stdio_.shutdown();
            stderr_.shutdown();
            return 0;
        } catch (const std::exception& e) {
            xlog::l(XLOG_FLINE + " exception: %s", e.what());
        }
        return 0;
    }

    void kill(bool KillTreeToo) {
        auto proc_id = process_id_.exchange(0);
        if (proc_id == 0) {
            xlog::v(
                "Attempt to kill process which is not started or already killed");
            return;
        }

        if (KillTreeToo) {
            if (job_) {
                TerminateJobObject(job_, 0);
                CloseHandle(job_);
                job_ = nullptr;
            } else {
                KillProcessTree(proc_id);
            }

            return;
        }

        if (exit_code_ == STILL_ACTIVE) {
            auto success = cma::tools::win::KillProcess(proc_id, -1);
            if (!success)
                xlog::v("Failed kill {} status {}", proc_id, GetLastError());
        }
    }

    const auto getCmdLine() const { return cmd_line_; }
    const auto processId() const { return process_id_.load(); }
    const auto exitCode() const { return exit_code_; }
    const auto getStdioRead() const { return stdio_.getRead(); }
    const auto getStderrRead() const { return stderr_.getRead(); }

    const auto& getData() const { return data_; }

    auto& getData() { return data_; }
    bool trySetExitCode(uint32_t Pid, uint32_t Code) {
        if (Pid && Pid == process_id_) {
            exit_code_ = Code;
            return true;
        }
        return false;
    }

private:
    const bool use_job_ = true;
    void setExitCode(uint32_t Code) { exit_code_ = Code; }
    std::wstring cmd_line_;
    std::atomic<uint32_t> process_id_;
    HANDLE job_;
    SimplePipe stdio_;
    SimplePipe stderr_;

    // output
    std::vector<char> data_;
    uint32_t exit_code_;
};

class ServiceController {
private:
    // we have to have data global
    static std::mutex s_lock_;
    static ServiceController* s_controller_;  // probably we need her shared
                                              // ptr, but this is clear overkill

public:
    // owns Processor
    ServiceController(BaseServiceProcessor* Processor) {
        assert(Processor);  // #TODO replace with own crash and log
        if (!Processor) return;

        std::lock_guard lk(s_lock_);
        if (!processor_ && s_controller_ == nullptr) {
            processor_.reset(Processor);
            s_controller_ = this;
        }
    }

    // no copy!
    ServiceController(const ServiceController& Rhs) = delete;
    ServiceController& operator=(const ServiceController& Rhs) = delete;

    // TODO: we may change it in the future
    ServiceController(ServiceController&& Rhs) = delete;
    ServiceController& operator=(ServiceController&& Rhs) = delete;

    // Service object destructor.
    ~ServiceController() {
        std::lock_guard lk(s_lock_);
        if (s_controller_ && s_controller_ == this) s_controller_ = nullptr;
    }

    // no return from here till service ends
    bool registerAndRun(const wchar_t* ServiceName,  //
                        bool CanStop = true, bool CanShutdown = true,
                        bool CanPauseContinue = true);

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
    void setServiceStatus(DWORD CurrentState, DWORD Win32ExitCode = NO_ERROR,
                          DWORD WaitHint = 0) {
        static DWORD dwCheckPoint = 1;

        // Fill in the SERVICE_STATUS structure of the service.

        status_.dwCurrentState = CurrentState;
        status_.dwWin32ExitCode = Win32ExitCode;
        status_.dwWaitHint = WaitHint;

        status_.dwCheckPoint = ((CurrentState == SERVICE_RUNNING) ||
                                (CurrentState == SERVICE_STOPPED))
                                   ? 0
                                   : dwCheckPoint++;

        // Report the status of the service to the SCM.
        auto ret = ::SetServiceStatus(status_handle_, &status_);
        xlog::l("Setting state %d result %d", CurrentState,
                ret ? 0 : GetLastError())
            .print();
    }

private:
    void initStatus(bool CanStop, bool CanShutdown, bool CanPauseContinue);

    // Entry point for the service. It registers the handler function for
    // the service and starts the service. NO RETURN FROM HERE when service
    // running.
    static void WINAPI ServiceMain(DWORD Argc, wchar_t** Argv) {
        // Register the handler function for the service
        xlog::l("Service Main").print();
        s_controller_->Start(Argc, Argv);
    }

    void Start(DWORD Argc, wchar_t** Argv);
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
    static void WINAPI ServiceCtrlHandler(DWORD dwCtrl) {
        switch (dwCtrl) {
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

    // The singleton service instance.
    std::unique_ptr<BaseServiceProcessor> processor_;
    const wchar_t* log_name_ = wtools::kWToolsLogName;

    // The name of the service
    std::unique_ptr<wchar_t[]> name_;
    bool can_stop_;
    bool can_shutdown_;
    bool can_pause_continue_;

    // The status of the service
    SERVICE_STATUS status_;

    // The service status handle
    SERVICE_STATUS_HANDLE status_handle_;
#if defined(GTEST_INCLUDE_GTEST_GTEST_H_)
    friend class ServiceControllerTest;
    FRIEND_TEST(ServiceControllerTest, CreateDelete);
    FRIEND_TEST(ServiceControllerTest, StartStop);
#endif

    std::vector<uint32_t> GetProcessListByParent(uint32_t ParentId) {
        using namespace std;
        PROCESSENTRY32 pe32;

        // Take a snapshot of all processes in the system.
        auto hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (hProcessSnap == INVALID_HANDLE_VALUE) {
            return {};
        };

        // Set the size of the structure before using it.
        pe32.dwSize = sizeof(PROCESSENTRY32);

        // Retrieve information about the first process,
        // and exit if unsuccessful
        if (!Process32First(hProcessSnap, &pe32)) {
            CloseHandle(hProcessSnap);  // clean the snapshot object
            return {};
        }
        ON_OUT_OF_SCOPE(CloseHandle(hProcessSnap));

        std::vector<uint32_t> processes;
        // Now walk the snapshot of processes
        do {
            wstring str(pe32.szExeFile);

            if (pe32.th32ParentProcessID == ParentId)
                processes.push_back(pe32.th32ProcessID);
        } while (Process32Next(hProcessSnap, &pe32));

        return processes;
    }
};

// standard converter, generates no exception in Windows but!
// we support two converters
// one is deprecated, second is windows only
// nice, yes?
// gtest [+]
inline std::string ConvertToUTF8(const std::wstring& Src) noexcept {
    using namespace std;
#if defined(WINDOWS_OS)
    // Windows only
    auto in_len = static_cast<int>(Src.length());
    auto out_len =
        ::WideCharToMultiByte(CP_UTF8, 0, Src.c_str(), in_len, NULL, 0, 0, 0);
    if (out_len == 0) return {};

    std::string str;
    try {
        str.resize(out_len);
    } catch (const std::exception& e) {
        xlog::l(XLOG_FUNC + "memory lacks %s", e.what());
        return {};
    }

    // convert
    ::WideCharToMultiByte(CP_UTF8, 0, Src.c_str(), -1, str.data(), out_len, 0,
                          0);
    return str;
#else
    // standard but deprecated
    try {
        return wstring_convert<codecvt_utf8<wchar_t> >().to_bytes(Src);
    } catch (const exception& e) {
        xlog::l("Failed to convert %ls", Src.c_str());
        return "";
    }
#endif  // endif
}

// standard Windows converter from Microsoft
// WINDOWS ONLY
// gtest [+] in yaml
inline std::wstring ConvertToUTF16(const std::string& Src) noexcept {
#if defined(WINDOWS_OS)
    auto in_len = static_cast<int>(Src.length());
    auto utf8_str = Src.c_str();
    auto out_len = MultiByteToWideChar(CP_UTF8, 0, utf8_str, in_len, NULL, 0);
    std::wstring wstr;
    try {
        wstr.resize(out_len);
    } catch (const std::exception& e) {
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

// Internal description of assorted counter params.
// Should be valid for all windows versions
struct CounterParam {
    const wchar_t* const description_;  // human form
    const wchar_t* const name_;         // usually number
    const uint32_t index_;              // the same as name
    const uint32_t counters_count;
    const uint32_t instances_min_;
    const uint32_t instances_max_;
};

// read MULTI_SZ string from the registry
std::vector<wchar_t> ReadPerfCounterKeyFromRegistry(bool LocalLanguage);
std::optional<uint32_t> FindPerfIndexInRegistry(const std::wstring& Key);
NameMap GenerateNameMap();

const CounterParam kCpuCounter = {L"Processor", L"238", 238, 15, 1, 33};
const CounterParam kDiskCounter = {L"Disk", L"234", 234, 31, 1, 16};

// ************************
// #TODO probably we need a class wrapper here
// ************************
// to simplify reading
using DataSequence = cma::tools::DataBlock<BYTE>;

// API:
// 1. Read data from registry
DataSequence ReadPerformanceDataFromRegistry(
    const std::wstring& CounterList) noexcept;

// 2. Find required object
const PERF_OBJECT_TYPE* FindPerfObject(const DataSequence& Db,
                                       DWORD counter_index) noexcept;

// 3. Get Instances and Names of Instances
std::vector<const PERF_INSTANCE_DEFINITION*> GenerateInstances(
    const PERF_OBJECT_TYPE* Object) noexcept;
std::vector<std::wstring> GenerateInstanceNames(
    const PERF_OBJECT_TYPE* Object) noexcept;

// 4. Get Counters
// INSTANCELESS!
std::vector<const PERF_COUNTER_DEFINITION*> GenerateCounters(
    const PERF_OBJECT_TYPE* Object,
    const PERF_COUNTER_BLOCK*& DataBlock) noexcept;

// INSTANCED
std::vector<const PERF_COUNTER_DEFINITION*> GenerateCounters(
    const PERF_OBJECT_TYPE* Object) noexcept;

// NAMES
std::vector<std::wstring> GenerateCounterNames(const PERF_OBJECT_TYPE* Object,
                                               const NameMap& Map);
// 5. And Values!
std::vector<ULONGLONG> GenerateValues(
    const PERF_COUNTER_DEFINITION& Counter,
    std::vector<const PERF_INSTANCE_DEFINITION*>& Instances) noexcept;

uint64_t GetValueFromBlock(const PERF_COUNTER_DEFINITION& Counter,
                           const PERF_COUNTER_BLOCK* Block) noexcept;

std::string GetName(uint32_t CounterType) noexcept;
}  // namespace perf

inline int64_t QueryPerformanceFreq() {
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
inline std::wstring GetCurrentExePath() noexcept {
    using namespace std;
    using namespace std::filesystem;

    wstring exe_path;
    int args_count = 0;
    auto arg_list = ::CommandLineToArgvW(GetCommandLineW(), &args_count);
    if (arg_list) {
        ON_OUT_OF_SCOPE(LocalFree(arg_list););
        path exe = arg_list[0];
        try {
            if (exists(exe)) {
                exe_path = exe.parent_path();
            }
        } catch (const std::exception&) {
            // not possible, btw, but policy is noexcept
        }
    }
    return exe_path;
}

// wrapper for win32 specific function
// return 0 when no data or error
// gtest [*] - internally used
inline int DataCountOnHandle(HANDLE Handle) {
    DWORD read_count = 0;

    // MSDN says to do so
    auto peek_result =
        ::PeekNamedPipe(Handle, nullptr, 0, nullptr, &read_count, nullptr);

    if (!peek_result) return 0;

    return read_count;
}

template <typename T>
std::string ConditionallyConvertFromUTF16(const std::vector<T>& Data) {
    if (Data.empty()) return {};
    bool convert_required =
        Data.data()[0] == '\xFF' && Data.data()[1] == '\xFE';

    std::string data;
    if (convert_required) {
        auto raw_data = reinterpret_cast<const wchar_t*>(Data.data() + 2);
        std::wstring wdata(raw_data, raw_data + (Data.size() - 2) / 2);
        if (wdata.back() != 0) wdata += L'\0';
        data = wtools::ConvertToUTF8(wdata);
    } else {
        data.assign(Data.begin(), Data.end());
    }

    // trick to place in string 0 at the end
    if (data.back() != 0) {
        data.reserve(data.size() + 1);
        data.data()[data.size()] = 0;
    }

    return data;
}

// local implementation of shitty registry access functions
inline uint32_t LocalReadUint32(const char* RootName, const char* Name,
                                uint32_t DefaultValue = 0) {
    HKEY hKey = 0;
    auto result =
        RegOpenKeyExA(HKEY_LOCAL_MACHINE, RootName, 0, KEY_QUERY_VALUE, &hKey);
    if (result != ERROR_SUCCESS) return DefaultValue;

    DWORD value = 0;
    DWORD type = REG_DWORD;
    DWORD size = sizeof(DWORD);
    result = RegQueryValueExA(hKey, Name, 0, &type, (PBYTE)&value, &size);
    RegCloseKey(hKey);

    if (result == ERROR_SUCCESS)
        return value;
    else
        return DefaultValue;
}

void InitWindowsCom();
void CloseWindowsCom();
bool IsWindowsComInitialized();
bool InitWindowsComSecurity();

// Low Level Utilities to access and convert VARIANT
inline int32_t WmiGetInt32(const VARIANT& Var) noexcept {
    switch (Var.vt) {
            // 8 bits values
        case VT_UI1:
            return static_cast<int32_t>(Var.bVal);
        case VT_I1:
            return static_cast<int32_t>(Var.cVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<int32_t>(Var.uiVal);
        case VT_I2:
            return static_cast<int32_t>(Var.iVal);
            // 32 bits values
        case VT_UI4:
            return static_cast<int32_t>(Var.uintVal);
        case VT_I4:
            return Var.intVal;  // no conversion here, we expect good type here
        default:
            return 0;
    }
}

inline uint32_t WmiGetUint32(const VARIANT& Var) noexcept {
    switch (Var.vt) {
            // 8 bits values
        case VT_UI1:
            return static_cast<uint32_t>(Var.bVal);
        case VT_I1:
            return static_cast<uint32_t>(Var.cVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<uint32_t>(Var.uiVal);
        case VT_I2:
            return static_cast<uint32_t>(Var.iVal);
            // 32 bits values
        case VT_UI4:
            return Var.uintVal;  // no conversion here, we expect good type here
        case VT_I4:
            return static_cast<uint32_t>(Var.uintVal);
        default:
            return 0;
    }
}

// Low Level Utilities to access and convert VARIANT
inline int64_t WmiGetInt64(const VARIANT& Var) noexcept {
    switch (Var.vt) {
            // 8 bits values
        case VT_UI1:
            return static_cast<int64_t>(Var.bVal);
        case VT_I1:
            return static_cast<int64_t>(Var.cVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<int64_t>(Var.uiVal);
        case VT_I2:
            return static_cast<int64_t>(Var.iVal);
            // 64 bits values
        case VT_UI4:
            return static_cast<int64_t>(Var.uintVal);
        case VT_I4:
            return static_cast<int64_t>(Var.intVal);
        case VT_UI8:
            return static_cast<int64_t>(Var.ullVal);
        case VT_I8:
            return Var.llVal;  // no conversion here, we expect good type here
        default:
            return 0;
    }
}

inline uint64_t WmiGetUint64(const VARIANT& Var) noexcept {
    switch (Var.vt) {
            // 8 bits values
        case VT_UI1:
            return static_cast<uint64_t>(Var.bVal);
        case VT_I1:
            return static_cast<uint64_t>(Var.cVal);
            // 16 bits values
        case VT_UI2:
            return static_cast<uint64_t>(Var.uiVal);
        case VT_I2:
            return static_cast<uint64_t>(Var.iVal);
        case VT_UI4:
            return static_cast<uint64_t>(Var.uintVal);
        case VT_I4:
            return static_cast<uint64_t>(Var.uintVal);
        case VT_UI8:
            return Var.ullVal;  // no conversion here, we expect good type here
        case VT_I8:
            return static_cast<uint64_t>(Var.llVal);
        default:
            return 0;
    }
}

// gtest[-]
inline bool WmiObjectContains(IWbemClassObject* Object,
                              const std::wstring& Name) {
    assert(Object);
    VARIANT value;
    HRESULT res = Object->Get(Name.c_str(), 0, &value, nullptr, nullptr);
    if (FAILED(res)) {
        return false;
    }
    ON_OUT_OF_SCOPE(VariantClear(&value));
    return value.vt != VT_NULL;
}

std::wstring WmiGetWstring(const VARIANT& Var);
std::optional<std::wstring> WmiTryGetString(IWbemClassObject* Object,
                                            const std::wstring& Name);
std::wstring WmiStringFromObject(IWbemClassObject* Object,
                                 const std::vector<std::wstring>& Names);
std::wstring WmiStringFromObject(IWbemClassObject* Object,
                                 const std::wstring& Name);
std::vector<std::wstring> WmiGetNamesFromObject(IWbemClassObject* WmiObject);

uint64_t WmiUint64FromObject(IWbemClassObject* Object,
                             const std::wstring& Name);

IEnumWbemClassObject* WmiExecQuery(IWbemServices* Services,
                                   const std::wstring& Query) noexcept;
IWbemClassObject* WmiGetNextObject(IEnumWbemClassObject* Enumerator);

// the class is thread safe(theoretisch)
class WmiWrapper {
public:
    // first call
    bool open() noexcept;

    // second call
    bool connect(const std::wstring& NameSpace) noexcept;

    // This is OPTIONAL feature, LWA doesn't use it
    bool impersonate() noexcept;

    std::wstring produceTable(IEnumWbemClassObject* Enumerator,
                              const std::vector<std::wstring>& Names) noexcept;

    // work horse to ask certain names from the target
    // on error returns empty string
    std::wstring queryTable(const std::vector<std::wstring> Names,
                            const std::wstring& Target) noexcept;

    // special purposes: formatting for PS for example
    // on error returns nullptr
    // You have to call Release for returned object!!!
    IEnumWbemClassObject* queryEnumerator(const std::vector<std::wstring> Names,
                                          const std::wstring& Target) noexcept;

private:
    // build valid WQL query
    static std::wstring makeQuery(const std::vector<std::wstring> Names,
                                  const std::wstring& Target) noexcept;

    mutable std::mutex lock_;
    IWbemLocator* locator_;
    IWbemServices* services_;
};

HMODULE LoadWindowsLibrary(const std::wstring DllPath);
// Look into the registry in order to find out, which
// event logs are available
// return false only when something wrong with registry
std::vector<std::string> EnumerateAllRegistryKeys(const char* RegPath);

}  // namespace wtools

#endif  // wtools_h__
