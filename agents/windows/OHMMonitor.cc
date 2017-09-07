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

#include "OHMMonitor.h"
#include "Logger.h"
#include "WinApiAdaptor.h"
#include "types.h"

OHMMonitor::OHMMonitor(const std::string &bin_path, Logger *logger,
                       const WinApiAdaptor &winapi)
    : _exe_path(bin_path + "\\OpenHardwareMonitorCLI.exe")
    , _logger(logger)
    , _winapi(winapi) {
    _available = (_winapi.GetFileAttributes(_exe_path.c_str()) !=
                  INVALID_FILE_ATTRIBUTES);
}

OHMMonitor::~OHMMonitor() {
    if (_current_process != INVALID_HANDLE_VALUE) {
        DWORD exitCode = 0;
        if (!_winapi.GetExitCodeProcess(_current_process, &exitCode)) {
            // invalid handle
            _winapi.CloseHandle(_current_process);
        } else {
            if (exitCode == STILL_ACTIVE) {
                // shut down ohm process
                _winapi.TerminateProcess(_current_process, 0);
            }
            _winapi.CloseHandle(_current_process);
        }
    }
}

HANDLE dev_null(const WinApiAdaptor &winapi) {
    SECURITY_ATTRIBUTES secattr = {};
    secattr.nLength = sizeof(SECURITY_ATTRIBUTES);
    secattr.lpSecurityDescriptor = NULL;
    secattr.bInheritHandle = TRUE;
    return winapi.CreateFile("nul:", GENERIC_READ | GENERIC_WRITE,
                             FILE_SHARE_READ | FILE_SHARE_WRITE, &secattr,
                             OPEN_EXISTING, 0, nullptr);
}

bool OHMMonitor::checkAvailabe() {
    if (!_available) {
        return false;
    }

    if (_current_process != INVALID_HANDLE_VALUE) {
        DWORD exitCode = 0;
        if (!_winapi.GetExitCodeProcess(_current_process, &exitCode)) {
            // handle invalid???
            Debug(_logger) << "ohm process handle invalid";
            _winapi.CloseHandle(_current_process);
            _current_process = INVALID_HANDLE_VALUE;
        } else {
            if (exitCode != STILL_ACTIVE) {
                Debug(_logger)
                    << "OHM process ended with exit code " << exitCode;
                _winapi.CloseHandle(_current_process);
                _current_process = INVALID_HANDLE_VALUE;
            }
        }
    }

    if (_current_process == INVALID_HANDLE_VALUE) {
        STARTUPINFO si = {};
        si.cb = sizeof(STARTUPINFO);
        si.dwFlags |= STARTF_USESTDHANDLES;
        si.hStdOutput = si.hStdError = dev_null(_winapi);

        OnScopeExit close_stdout([&]() { _winapi.CloseHandle(si.hStdOutput); });

        PROCESS_INFORMATION pi = {};

        if (!_winapi.CreateProcess(_exe_path.c_str(), nullptr, nullptr, nullptr,
                                   TRUE, 0, nullptr, nullptr, &si, &pi)) {
            Error(_logger) << "failed to run %s" << _exe_path;
            return false;
        } else {
            _current_process = pi.hProcess;
            Debug(_logger) << "started " << _exe_path << " (pid "
                           << pi.dwProcessId << ")";
            _winapi.CloseHandle(pi.hThread);
        }
    }
    return true;
}
