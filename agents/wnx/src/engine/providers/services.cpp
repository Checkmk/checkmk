// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/services.h"

#include <ranges>
#include <string>
#include <utility>

#include "tools/_raii.h"

namespace rs = std::ranges;

namespace cma::provider {
namespace {

DWORD GetServiceStartDword(SC_HANDLE manager_handle,
                           const wchar_t *service_name) {
    // Query the start type of the service
    auto *handle =
        ::OpenServiceW(manager_handle, service_name, SERVICE_QUERY_CONFIG);
    if (handle == nullptr) {
        return -1;
    }

    ON_OUT_OF_SCOPE(CloseServiceHandle(handle));

    DWORD bytes_required = 0;
    if (::QueryServiceConfig(handle, nullptr, 0, &bytes_required) == TRUE) {
        return -1;
    }

    if (::GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
        return -1;
    }

    auto buffer = std::make_unique<unsigned char[]>(bytes_required);
    auto *query_service_config =
        reinterpret_cast<LPQUERY_SERVICE_CONFIGW>(buffer.get());

    if (::QueryServiceConfig(handle, query_service_config, bytes_required,
                             &bytes_required) == FALSE) {
        return -1;
    }

    return query_service_config->dwStartType;
}

std::string_view GetServiceStartType(SC_HANDLE manager_handle,
                                     const wchar_t *service_name) {
    switch (GetServiceStartDword(manager_handle, service_name)) {
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
std::string_view ConvertState2Name(unsigned long state) {
    switch (state) {
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

std::pair<DWORD, DWORD> EnumAllServices(SC_HANDLE handle) {
    DWORD bytes_needed{0};
    DWORD num_services{0};

    ::EnumServicesStatusExW(handle, SC_ENUM_PROCESS_INFO, SERVICE_WIN32,
                            SERVICE_STATE_ALL, nullptr, 0, &bytes_needed,
                            &num_services, nullptr, nullptr);

    return {bytes_needed, num_services};
}
}  // namespace

std::string Services::makeBody() {
    auto *handle = ::OpenSCManager(
        nullptr, nullptr, SC_MANAGER_CONNECT | SC_MANAGER_ENUMERATE_SERVICE);

    if (handle == nullptr) {
        XLOG::l("OpenSCManager Failed with error '{}'", GetLastError());
        return {};
    }

    ON_OUT_OF_SCOPE(::CloseServiceHandle(handle));

    // How many data and service we have to check:
    auto [bytes_needed, num_services] = EnumAllServices(handle);

    if (::GetLastError() != ERROR_MORE_DATA || bytes_needed == 0) {
        XLOG::l("OpenSCManager Failed with error '{}'", ::GetLastError());
        return {};
    }

    // read data about service into local buffer
    auto buffer = std::make_unique<unsigned char[]>(bytes_needed);
    if (FALSE == ::EnumServicesStatusExW(
                     handle, SC_ENUM_PROCESS_INFO, SERVICE_WIN32,
                     SERVICE_STATE_ALL, buffer.get(), bytes_needed,
                     &bytes_needed, &num_services, nullptr, nullptr)) {
        XLOG::l("EnumServices Failed with error {}", GetLastError());
        return {};
    }

    // according to MSDN buffer is ENUM_SERVICE_STATUS_PROCESSW[]
    auto *service =
        reinterpret_cast<ENUM_SERVICE_STATUS_PROCESSW *>(buffer.get());

    std::string out;
    for (unsigned i = 0; i < num_services; i++) {
        const auto state = service->ServiceStatusProcess.dwCurrentState;

        auto state_name = ConvertState2Name(state);

        auto service_name = wtools::ToUtf8(service->lpServiceName);
        rs::replace(service_name, ' ', '_');

        auto start_type = GetServiceStartType(handle, service->lpServiceName);

        out += fmt::format("{} {}/{} {}\n",  // main string format
                           service_name,     // name
                           state_name,       // state
                           start_type,       // start
                           wtools::ToUtf8(service->lpDisplayName));

        ++service;
    }

    return out;
}

}  // namespace cma::provider
