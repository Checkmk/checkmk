// Windows Tools
#include <stdafx.h>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <WinSock2.h>

#include <iostream>

#include <stdio.h>
#include <cstdint>
#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "cfg.h"
#include "logger.h"
#include "wtools.h"

#pragma comment(lib, "wbemuuid.lib")  /// Microsoft Specific

namespace wtools {
std::mutex ServiceController::s_lock_;
ServiceController* ServiceController::s_controller_ = nullptr;


// no return from here
// can print on screen
bool ServiceController::registerAndRun(const wchar_t* ServiceName,  //
                                       bool CanStop,                // t
                                       bool CanShutdown,            // t
                                       bool CanPauseContinue) {     // t
    if (!processor_) {
        XLOG::l.bp("No processor");
        return false;
    }
    if (!ServiceName) {
        XLOG::l.bp("No Service name");
        return false;
    }

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
    DWORD ret = 0;
    try {
        ret = StartServiceCtrlDispatcher(serviceTable);
        if (!ret) {
            XLOG::l(XLOG::kStdio)("Cannot Start Service '{}' error = '{}'",
                                  ConvertToUTF8(ServiceName), GetLastError());
        }
    } catch (...) {
        XLOG::l(XLOG::kStdio)("Exception in Service start with error {}",
                              GetLastError());
        ret = -1;
    }
	
    return ret == 0;
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
                    uint32_t dwStartType, const wchar_t* Dependencies,
                    const wchar_t* Account, const wchar_t* Password) {
    wchar_t service_path[MAX_PATH];

    if (::GetModuleFileName(NULL, service_path, ARRAYSIZE(service_path)) == 0) {
        XLOG::l.crit("GetModuleFileName failed w/err {:#X}", GetLastError());
        return false;
    }

    // Open the local default service control manager database
    auto service_manager = ::OpenSCManager(
        NULL, NULL, SC_MANAGER_CONNECT | SC_MANAGER_CREATE_SERVICE);
    if (!service_manager) {
        XLOG::l.crit("OpenSCManager failed w/err {:#X}", GetLastError());
        return false;
    }

    ON_OUT_OF_SCOPE(CloseServiceHandle(service_manager););

    // Install the service into SCM by calling CreateService
    auto service = ::CreateService(service_manager,       // SCManager database
                                   ServiceName,           // Name of service
                                   DisplayName,           // Name to display
                                   SERVICE_QUERY_STATUS,  // Desired access
                                   SERVICE_WIN32_OWN_PROCESS,  // Service type
                                   dwStartType,           // Service start type
                                   SERVICE_ERROR_NORMAL,  // Error control type
                                   service_path,          // Service's binary
                                   NULL,          // No load ordering group
                                   NULL,          // No tag identifier
                                   Dependencies,  // Dependencies
                                   Account,       // Service running account
                                   Password       // Password of the account
    );
    if (!service) {
        std::cout << XLOG::l.crit("CreateService failed w/err {}",
                                  GetLastError());
        return false;
    }
    ON_OUT_OF_SCOPE(CloseServiceHandle(service););

    XLOG::l.i("'{}' is installed.", ConvertToUTF8(ServiceName));
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
bool UninstallService(const wchar_t* ServiceName) {
    // Open the local default service control manager database
    auto service_manager = ::OpenSCManager(NULL, NULL, SC_MANAGER_CONNECT);
    if (!service_manager) {
        xlog::l(L"OpenSCManager failed w/err 0x%08lx\n", GetLastError())
            .print();
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(service_manager););

    // Open the service with delete, stop, and query status permissions
    auto service = ::OpenService(service_manager, ServiceName,
                                 SERVICE_STOP | SERVICE_QUERY_STATUS | DELETE);
    if (!service) {
        xlog::l(L"OpenService failed w/err 0x%08lx\n", GetLastError()).print();
        return false;
    }
    ON_OUT_OF_SCOPE(::CloseServiceHandle(service););

    // Try to stop the service
    SERVICE_STATUS ssSvcStatus = {};
    if (::ControlService(service, SERVICE_CONTROL_STOP, &ssSvcStatus)) {
        xlog::l(L"Stopping %s.", ServiceName).print();
        Sleep(1000);

        while (::QueryServiceStatus(service, &ssSvcStatus)) {
            if (ssSvcStatus.dwCurrentState == SERVICE_STOP_PENDING) {
                xlog::l(L".").print();
                Sleep(1000);
            } else
                break;
        }

        if (ssSvcStatus.dwCurrentState == SERVICE_STOPPED) {
            xlog::l(L"\n%s is stopped.\n", ServiceName).print();
        } else {
            xlog::l(L"\n%s failed to stop.\n", ServiceName).print();
        }
    }

    // Now remove the service by calling DeleteService.
    if (!::DeleteService(service)) {
        xlog::l(L"DeleteService failed w/err 0x%08lx\n", GetLastError())
            .print();
        return false;
    }

    xlog::l(L"%s is removed.\n", ServiceName).print();
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
    if (!processor_) return;  // #TODO: trace

    // Register the handler function for the service
    status_handle_ =
        RegisterServiceCtrlHandler(name_.get(), ServiceCtrlHandler);
    if (!status_handle_) {
        XLOG::l(XLOG::kStdio)("I cannot register damned handlers %d",
                              GetLastError());
        throw GetLastError();  // crash here
        return;
    }
    xlog::l("Damned handlers registered");

    try {
        // Tell SCM that the service is starting.
        setServiceStatus(SERVICE_START_PENDING);

        // Perform service-specific initialization.
        processor_->startService();

        // Tell SCM that the service is started.
        setServiceStatus(SERVICE_RUNNING);
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

// Window s specific performance counters
// Functions are from OWA/MSDN
// No exceptions
// C-like here to be more windows
namespace perf {

// read MULTI_SZ string from the registry
// #TODO gtest
std::vector<wchar_t> ReadPerfCounterKeyFromRegistry(bool LocalLanguage) {
    DWORD counters_size = 0;

    auto key = LocalLanguage ? HKEY_PERFORMANCE_NLSTEXT : HKEY_PERFORMANCE_TEXT;

    // preflight
    ::RegQueryValueExW(key, L"Counter", nullptr, nullptr, nullptr,
                       &counters_size);
    if (counters_size == 0) {
        XLOG::l("SOmething is really wrong");
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

std::optional<uint32_t> FindPerfIndexInRegistry(const std::wstring& Key) {
    if (Key.empty()) return {};

    for (auto national : {true, false}) {
        auto counter_str =
            wtools::perf::ReadPerfCounterKeyFromRegistry(national);
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
    NameMap nm;
    auto counter_str = wtools::perf::ReadPerfCounterKeyFromRegistry(false);
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
// #TODO gtest
// DataSequence is primitive wrapper over data buffer
// DataSequence takes ownership over buffer
DataSequence ReadPerformanceDataFromRegistry(
    const std::wstring& CounterName) noexcept {
    DWORD buf_size = 40000;
    BYTE* buffer = nullptr;

    while (1) {
        // allocation(a bit stupid, but we do not want top have STL inside
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
        // iterate to the object we requested since apparently there can be more
        // than that in the buffer returned
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
        xlog::l(XLOG_FLINE + " exception: %s", e.what());
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
        XLOG::l(XLOG_FLINE + " disaster in names: {}", e.what());
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
        XLOG::l(XLOG_FLINE + " disaster in instance less counters: {}",
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
            // handle other data generically. This is wrong in some situation.
            // Once upon a time in future we might implement a conversion as
            // described in
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
        xlog::l(XLOG_FLINE + " exception:%s", e.what());
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

static std::mutex ComLock;
static bool WindowsComInitialized = false;  // #VIP #Global
                                            // controls availability of WMI

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
        XLOG::l.w("Stupid Windows {:#X}", (unsigned)hres);
        return true;
    }
    if (FAILED(hres)) {
        XLOG::l.crit("Error Windows Security {:X}", (unsigned)hres);
        return false;  // Program has failed.
    }

    XLOG::l.i("COM Initialized");

    return true;
}

void InitWindowsCom() {
    std::lock_guard lk(ComLock);
    if (WindowsComInitialized) return;
    auto hres = CoInitializeEx(0, COINIT_MULTITHREADED);
    WORD wVersionRequested;
    WSADATA wsaData;
    int err;

    /* Use the MAKEWORD(lowbyte, highbyte) macro declared in Windef.h */
    wVersionRequested = MAKEWORD(2, 2);

    err = WSAStartup(wVersionRequested, &wsaData);
    if (err != 0) {
        /* Tell the user that we could not find a usable */
        /* Winsock DLL.                                  */
        printf("WSAStartup failed with error: %d\n", err);
        return;
    }

    if (FAILED(hres)) {
        XLOG::l.crit("Can't init COM {:#X}", (unsigned)hres);
        return;
    }
    auto ret = InitWindowsComSecurity();
    if (!ret) {
        XLOG::l.crit("Can't init COM SECURITY ");
        CoUninitialize();
        return;
    }

    XLOG::l.i("COM initialized");

    WindowsComInitialized = true;
}

void CloseWindowsCom() {
    std::lock_guard lk(ComLock);
    if (!WindowsComInitialized) return;
    CoUninitialize();
    XLOG::l.i("COM closed");
    WindowsComInitialized = false;
}

bool IsWindowsComInitialized() {
    std::lock_guard lk(ComLock);
    return WindowsComInitialized;
}

std::wstring WmiGetWstring(const VARIANT& Var) {
    if (Var.vt & VT_ARRAY) {
        // XLOG::l.w("Array is not supported");
        return L"<array>";
    }
    if (Var.vt & VT_VECTOR) {
        // XLOG::l.w("Vector is not supported");
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
            return std::to_wstring(WmiGetInt32(Var));
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
            XLOG::l.crit("Unknown data type in Vector {}", Var.vt);
            return L"";
    }
}

std::wstring WmiStringFromObject(IWbemClassObject* Object,
                                 const std::vector<std::wstring>& Names) {
    std::wstring result;
    for (auto& name : Names) {
        // data
        VARIANT value;
        // Get the value of the Name property
        auto hres = Object->Get(name.c_str(), 0, &value, 0, 0);
        if (SUCCEEDED(hres)) {
            ON_OUT_OF_SCOPE(VariantClear(&value));
            result += wtools::WmiGetWstring(value) + L",";
        }
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
    auto hres = Object->Get(Name.c_str(), 0, &value, 0, 0);
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
    auto hres = Object->Get(Name.c_str(), 0, &value, 0, 0);
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
    auto hres = Object->Get(Name.c_str(), 0, &value, 0, 0);
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
    if (FAILED(res) || !names) {
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

        result.push_back(std::wstring(property_name));
    }

    return result;
}

// returns valid enumerator or nullptr
IEnumWbemClassObject* WmiExecQuery(IWbemServices* Services,
                                   const std::wstring& Query) noexcept {
    XLOG::l.t("Query is {}", ConvertToUTF8(Query));
    IEnumWbemClassObject* enumerator = nullptr;
    auto hres = Services->ExecQuery(
        bstr_t("WQL"),          // always the same
        bstr_t(Query.c_str()),  // text of query
        WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY,  // legacy agent
        nullptr,                                                // nobody knows
        &enumerator);

    if (SUCCEEDED(hres)) return enumerator;
    // SHOULD NOT HAPPEN
    XLOG::l.e("Failed query wmi {:#X}, query is {}", (unsigned)hres,
              ConvertToUTF8(Query));
    return nullptr;  // Program has failed.
}

bool WmiWrapper::open() noexcept {  // Obtain the initial locator to Windows
                                    // Management
                                    // on a particular host computer.
    std::lock_guard lk(lock_);
    IWbemLocator* locator = 0;

    auto hres = CoCreateInstance(CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER,
                                 IID_IWbemLocator, (LPVOID*)&locator);

    if (FAILED(hres)) {
        XLOG::l.crit("Can't Create Instance WMI {:#X}",
                     static_cast<unsigned long>(hres));
        return false;  // Program has failed.
    }
    locator_ = locator;
    return true;
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
    if (!locator_) {
        XLOG::l.crit(XLOG_FUNC + " what about open before connect?");
        return false;
    }

    if (services_) {
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
                                0,                           // Locale
                                0,                           // Security flags
                                0,                           // Authority
                                0,                           // Context object
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
    if (!services_) {
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

    XLOG::l.e("Failed blanker/impersonation locator wmI {X}", hres);
    return false;  // Program has failed.
}

// tested implicitly
// returns nullptr on any error
IWbemClassObject* WmiGetNextObject(IEnumWbemClassObject* Enumerator) {
    if (!Enumerator) {
        XLOG::l.e("nullptr in Enumerator");
        return nullptr;
    }
    ULONG returned = 0;
    IWbemClassObject* wmi_object = nullptr;

    auto timeout = cma::cfg::groups::global.getWmiTimeout();
    auto hres = Enumerator->Next(timeout * 1000, 1, &wmi_object,
                                 &returned);  // legacy code
    if (WBEM_S_TIMEDOUT == hres) {
        XLOG::l.e("Timeout {} seconds broken  when query WMI - RETRY:",
                  timeout);
        return nullptr;
    }

    if (WBEM_S_FALSE == hres) return nullptr;  // no more data
    if (WBEM_NO_ERROR != hres) {
        XLOG::l.t("Return {:#X} probably object doesn't exist",
                  static_cast<unsigned int>(hres));
        return nullptr;
    }
    if (0 == returned) return nullptr;  // eof

    return wmi_object;
}

std::wstring WmiWrapper::produceTable(
    IEnumWbemClassObject* Enumerator,
    const std::vector<std::wstring>& Names) noexcept {
    std::wstring result;
    ULONG returned = 0;
    IWbemClassObject* wmi_object = nullptr;
    bool print_names_please = true;
    // setup default names vector
    auto names = Names;

    while (Enumerator) {
        wmi_object = WmiGetNextObject(Enumerator);
        if (!wmi_object) break;

        // names
        if (print_names_please) {
            if (Names.empty()) {
                // we have asking for everything, ergo we have to use
                // get name list from WMI
                names = std::move(wtools::WmiGetNamesFromObject(wmi_object));
            }
            result = cma::tools::JoinVector(names, L",");
            if (result.empty()) {
                XLOG::l.e("Failed to get names");
            } else
                result += L'\n';
            print_names_please = false;
        }

        auto raw = wtools::WmiStringFromObject(wmi_object, names);
        if (!raw.empty()) result += raw + L"\n";

        wmi_object->Release();
        wmi_object = nullptr;
    }
    return result;
}

std::wstring WmiWrapper::makeQuery(const std::vector<std::wstring> Names,
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
// on error returns empty string
std::wstring WmiWrapper::queryTable(const std::vector<std::wstring> Names,
                                    const std::wstring& Target) noexcept {
    auto query_text = makeQuery(Names, Target);

    // Send a query to system
    std::lock_guard lk(lock_);
    auto enumerator = wtools::WmiExecQuery(services_, query_text);

    // make a table using enumerator and supplied Names vector
    if (!enumerator) {
        return {};
    }
    ON_OUT_OF_SCOPE(enumerator->Release());

    return produceTable(enumerator, Names);
}

// special purposes: formatting for PS for example
// on error returns nullptr
// Release MUST!!!
IEnumWbemClassObject* WmiWrapper::queryEnumerator(
    const std::vector<std::wstring> Names,
    const std::wstring& Target) noexcept {
    auto query_text = makeQuery(Names, Target);

    // Send a query to system
    std::lock_guard lk(lock_);
    return wtools::WmiExecQuery(services_, query_text);
}

HMODULE LoadWindowsLibrary(const std::wstring DllPath) {
    // this should be sufficient most of the time
    static const size_t buffer_size = 128;

    std::wstring dllpath_expanded;
    dllpath_expanded.resize(buffer_size, '\0');
    DWORD required = ExpandEnvironmentStringsW(
        DllPath.c_str(), &dllpath_expanded[0], (DWORD)dllpath_expanded.size());

    if (required > dllpath_expanded.size()) {
        dllpath_expanded.resize(required + 1);
        required =
            ExpandEnvironmentStringsW(DllPath.c_str(), &dllpath_expanded[0],
                                      (DWORD)dllpath_expanded.size());
    } else if (required == 0) {
        dllpath_expanded = DllPath;
    }
    if (required != 0) {
        // required includes the zero terminator
        dllpath_expanded.resize(required - 1);
    }

    // load the library as a datafile without loading referenced dlls. This is
    // quicker but most of all it prevents problems if dependent dlls can't be
    // loaded.
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
        XLOG::l(" Cannot open registry key {} error {}", RegPath,
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
            XLOG::l("Failed to enum {} error {}", key_name, r);
            break;
        }
        entries.push_back(key_name);
    };
    return entries;
}

}  // namespace wtools

// verified code from the legacy client
// gtest is not required
inline SOCKET RemoveSocketInheritance(SOCKET OldSocket) {
    HANDLE new_handle = 0;

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
