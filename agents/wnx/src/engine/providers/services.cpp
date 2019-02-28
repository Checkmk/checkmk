
// provides basic api to start and stop service
#include "stdafx.h"

#include <string>

#include "tools/_raii.h"
#include "tools/_xlog.h"

#include "providers/services.h"

namespace cma {

namespace provider {

static const char *GetServiceStartType(SC_HANDLE Handle, LPCWSTR service_name) {
    // Query the start type of the service
    auto handle = ::OpenServiceW(Handle, service_name, SERVICE_QUERY_CONFIG);
    if (!handle) return "invalid1";

    ON_OUT_OF_SCOPE(CloseServiceHandle(handle));

    DWORD bytes_required = 0;
    if (::QueryServiceConfig(handle, NULL, 0, &bytes_required))
        return "invalid2";  // should not happen!

    if (::GetLastError() != ERROR_INSUFFICIENT_BUFFER) return "invalid3";

    auto buf_size = bytes_required;
    auto buffer = std::make_unique<unsigned char[]>(buf_size);
    auto lpsc = reinterpret_cast<LPQUERY_SERVICE_CONFIGW>(buffer.get());

    if (!::QueryServiceConfig(handle, lpsc, buf_size, &bytes_required))
        return "invalid4";  // should not happen!

    switch (lpsc->dwStartType) {
        case SERVICE_AUTO_START:
            return "auto";
        case SERVICE_BOOT_START:
            return "boot";
        case SERVICE_DEMAND_START:
            return "demand";
        case SERVICE_DISABLED:
            return "disabled";
        case SERVICE_SYSTEM_START:
            return "system";
        default:
            return "other";
    }
}

// simple state-string converter
static const char *ConvertState2Name(int State) {
    switch (State) {
        case SERVICE_CONTINUE_PENDING:
            return "continuing";
        case SERVICE_PAUSE_PENDING:
            return "pausing";
        case SERVICE_PAUSED:
            return "paused";
        case SERVICE_RUNNING:
            return "running";
        case SERVICE_START_PENDING:
            return "starting";
        case SERVICE_STOP_PENDING:
            return "stopping";
        case SERVICE_STOPPED:
            return "stopped";
        default:
            return "unknown";
    }
}

static auto EnumAllServices(SC_HANDLE Handle) {
    DWORD bytes_needed = 0;
    DWORD num_services = 0;
    ::EnumServicesStatusExW(Handle, SC_ENUM_PROCESS_INFO, SERVICE_WIN32,
                            SERVICE_STATE_ALL, NULL, 0, &bytes_needed,
                            &num_services, 0, 0);

    return std::make_tuple(bytes_needed, num_services);
}

std::string Services::makeBody() const {
    using namespace std::chrono;

    XLOG::t(XLOG_FUNC + " entering");

    // Pre-History: open and close
    auto handle = ::OpenSCManager(
        0, 0, SC_MANAGER_CONNECT | SC_MANAGER_ENUMERATE_SERVICE);

    // check for fail:
    if (!handle) {
        XLOG::l("OpenSCManager Fialed with error {}", GetLastError());
        return {};
    }

    ON_OUT_OF_SCOPE(CloseServiceHandle(handle));

    // How many data and service we have to check:
    auto [bytes_needed, num_services] = EnumAllServices(handle);

    if (::GetLastError() != ERROR_MORE_DATA || bytes_needed == 0) {
        XLOG::l("OpenSCManager Failed with error {}", GetLastError());
        return {};
    }

    // read data about service into local buffer
    auto buffer = std::make_unique<unsigned char[]>(bytes_needed);
    if (!::EnumServicesStatusExW(handle, SC_ENUM_PROCESS_INFO, SERVICE_WIN32,
                                 SERVICE_STATE_ALL, buffer.get(), bytes_needed,
                                 &bytes_needed, &num_services, 0, 0)) {
        XLOG::l("EnumServices Failed with error {}", GetLastError());
        return {};
    }

    // according to msdn buffer is ENUM_SERVICE_STATUS_PROCESSW[]
    auto service =
        reinterpret_cast<ENUM_SERVICE_STATUS_PROCESSW *>(buffer.get());

    std::string out;
    for (unsigned i = 0; i < num_services; i++) {
        auto state = service->ServiceStatusProcess.dwCurrentState;

        auto state_name = ConvertState2Name(state);

        // replace in name ' ' with  '_'
        auto service_name = wtools::ConvertToUTF8(service->lpServiceName);
        std::replace(service_name.begin(), service_name.end(), ' ', '_');

        auto start_type = GetServiceStartType(handle, service->lpServiceName);

        out += fmt::format("{} {}/{} {}\n",  // main string format
                           service_name,     // name
                           state_name,       // state
                           start_type,       // start
                           wtools::ConvertToUTF8(service->lpDisplayName));

        ++service;
    }

    return out;
}

}  // namespace provider
};  // namespace cma
