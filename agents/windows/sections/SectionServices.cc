// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "SectionServices.h"
#include "Logger.h"
#include "SectionHeader.h"
#include "stringutil.h"
#include "types.h"

SectionServices::SectionServices(const Environment &env, Logger *logger,
                                 const WinApiInterface &winapi)
    : Section("services", env, logger, winapi,
              std::make_unique<DefaultHeader>("services", logger)) {}

// Determine the start type of a service. Unbelievable how much
// code is needed for that...
const char *SectionServices::serviceStartType(SC_HANDLE scm,
                                              LPCWSTR service_name) {
    // Query the start type of the service
    const char *start_type = "invalid1";
    ServiceHandle schService{
        _winapi.OpenServiceW(scm, service_name, SERVICE_QUERY_CONFIG), _winapi};
    if (schService) {
        start_type = "invalid2";
        DWORD dwBytesNeeded, cbBufSize;
        if (!_winapi.QueryServiceConfig(schService.get(), NULL, 0,
                                        &dwBytesNeeded)) {
            start_type = "invalid3";
            DWORD dwError = _winapi.GetLastError();
            if (dwError == ERROR_INSUFFICIENT_BUFFER) {
                start_type = "invalid4";
                cbBufSize = dwBytesNeeded;
                std::vector<BYTE> buffer(cbBufSize, 0);
                LPQUERY_SERVICE_CONFIGW lpsc =
                    reinterpret_cast<LPQUERY_SERVICE_CONFIGW>(buffer.data());
                if (_winapi.QueryServiceConfig(schService.get(), lpsc,
                                               cbBufSize, &dwBytesNeeded)) {
                    switch (lpsc->dwStartType) {
                        case SERVICE_AUTO_START:
                            start_type = "auto";
                            break;
                        case SERVICE_BOOT_START:
                            start_type = "boot";
                            break;
                        case SERVICE_DEMAND_START:
                            start_type = "demand";
                            break;
                        case SERVICE_DISABLED:
                            start_type = "disabled";
                            break;
                        case SERVICE_SYSTEM_START:
                            start_type = "system";
                            break;
                        default:
                            start_type = "other";
                    }
                }
            }
        }
    }
    return start_type;
}

bool SectionServices::produceOutputInner(std::ostream &out,
                                         const std::optional<std::string> &) {
    Debug(_logger) << "SectionServices::produceOutputInner";
    ServiceHandle scm{
        _winapi.OpenSCManager(
            0, 0, SC_MANAGER_CONNECT | SC_MANAGER_ENUMERATE_SERVICE),
        _winapi};
    if (scm) {
        DWORD bytes_needed = 0;
        DWORD num_services = 0;
        // first determine number of bytes needed
        _winapi.EnumServicesStatusExW(scm.get(), SC_ENUM_PROCESS_INFO,
                                      SERVICE_WIN32, SERVICE_STATE_ALL, NULL, 0,
                                      &bytes_needed, &num_services, 0, 0);
        if (_winapi.GetLastError() == ERROR_MORE_DATA && bytes_needed > 0) {
            std::vector<BYTE> buffer(bytes_needed, 0);

            if (_winapi.EnumServicesStatusExW(
                    scm.get(), SC_ENUM_PROCESS_INFO, SERVICE_WIN32,
                    SERVICE_STATE_ALL, buffer.data(), bytes_needed,
                    &bytes_needed, &num_services, 0, 0)) {
                ENUM_SERVICE_STATUS_PROCESSW *service =
                    reinterpret_cast<ENUM_SERVICE_STATUS_PROCESSW *>(
                        buffer.data());
                for (unsigned i = 0; i < num_services; i++) {
                    DWORD state = service->ServiceStatusProcess.dwCurrentState;
                    const char *state_name = "unknown";
                    switch (state) {
                        case SERVICE_CONTINUE_PENDING:
                            state_name = "continuing";
                            break;
                        case SERVICE_PAUSE_PENDING:
                            state_name = "pausing";
                            break;
                        case SERVICE_PAUSED:
                            state_name = "paused";
                            break;
                        case SERVICE_RUNNING:
                            state_name = "running";
                            break;
                        case SERVICE_START_PENDING:
                            state_name = "starting";
                            break;
                        case SERVICE_STOP_PENDING:
                            state_name = "stopping";
                            break;
                        case SERVICE_STOPPED:
                            state_name = "stopped";
                            break;
                    }

                    const char *start_type =
                        serviceStartType(scm.get(), service->lpServiceName);

                    // The service name usually does not contain spaces. But
                    // in some cases it does. We replace them with _ in
                    // order
                    // the keep it in one space-separated column. Since we
                    // own
                    // the buffer, we can simply change the name inplace.
                    for (LPWSTR w = service->lpServiceName; *w; ++w) {
                        if (*w == L' ') *w = L'_';
                    }

                    out << Utf8(service->lpServiceName) << " " << state_name
                        << "/" << start_type << " "
                        << Utf8(service->lpDisplayName) << "\n";
                    ++service;
                }
            }
        }
    }
    return true;
}
