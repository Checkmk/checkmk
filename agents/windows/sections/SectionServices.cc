// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

typedef short SHORT;
#include "SectionServices.h"
#include "../WinApiAdaptor.h"
#include "../stringutil.h"
//#include "../check_mk_agent_def.h"

SectionServices::SectionServices(const Environment &env, Logger *logger,
                                 const WinApiAdaptor &winapi)
    : Section("services", env, logger, winapi) {}

// Determine the start type of a service. Unbelievable how much
// code is needed for that...
const char *SectionServices::serviceStartType(SC_HANDLE scm,
                                              LPCWSTR service_name) {
    // Query the start type of the service
    const char *start_type = "invalid1";
    SC_HANDLE schService;
    LPQUERY_SERVICE_CONFIGW lpsc;
    schService = _winapi.OpenServiceW(scm, service_name, SERVICE_QUERY_CONFIG);
    if (schService) {
        start_type = "invalid2";
        DWORD dwBytesNeeded, cbBufSize;
        if (!_winapi.QueryServiceConfig(schService, NULL, 0, &dwBytesNeeded)) {
            start_type = "invalid3";
            DWORD dwError = _winapi.GetLastError();
            if (dwError == ERROR_INSUFFICIENT_BUFFER) {
                start_type = "invalid4";
                cbBufSize = dwBytesNeeded;
                lpsc = (LPQUERY_SERVICE_CONFIGW)_winapi.LocalAlloc(LMEM_FIXED,
                                                                   cbBufSize);
                if (_winapi.QueryServiceConfig(schService, lpsc, cbBufSize,
                                               &dwBytesNeeded)) {
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
                _winapi.LocalFree(lpsc);
            }
        }
        _winapi.CloseServiceHandle(schService);
    }
    return start_type;
}

bool SectionServices::produceOutputInner(std::ostream &out) {
    SC_HANDLE scm = _winapi.OpenSCManager(
        0, 0, SC_MANAGER_CONNECT | SC_MANAGER_ENUMERATE_SERVICE);
    if (scm != INVALID_HANDLE_VALUE) {
        DWORD bytes_needed = 0;
        DWORD num_services = 0;
        // first determine number of bytes needed
        _winapi.EnumServicesStatusExW(scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32,
                                      SERVICE_STATE_ALL, NULL, 0, &bytes_needed,
                                      &num_services, 0, 0);
        if (_winapi.GetLastError() == ERROR_MORE_DATA && bytes_needed > 0) {
            BYTE *buffer = (BYTE *)malloc(bytes_needed);
            if (buffer) {
                if (_winapi.EnumServicesStatusExW(
                        scm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32,
                        SERVICE_STATE_ALL, buffer, bytes_needed, &bytes_needed,
                        &num_services, 0, 0)) {
                    ENUM_SERVICE_STATUS_PROCESSW *service =
                        (ENUM_SERVICE_STATUS_PROCESSW *)buffer;
                    for (unsigned i = 0; i < num_services; i++) {
                        DWORD state =
                            service->ServiceStatusProcess.dwCurrentState;
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
                            serviceStartType(scm, service->lpServiceName);

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
                free(buffer);
            }
        }
        _winapi.CloseServiceHandle(scm);
    }
    return true;
}
