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
#include "LoggerAdaptor.h"
#include "types.h"

OHMMonitor::OHMMonitor(const std::string &bin_path, const LoggerAdaptor &logger)
    : _exe_path(bin_path + "\\OpenHardwareMonitorCLI.exe")
    , _logger(logger) {
    _available =
        ::GetFileAttributesA(_exe_path.c_str()) != INVALID_FILE_ATTRIBUTES;
}

OHMMonitor::~OHMMonitor() {
    if (_current_process != INVALID_HANDLE_VALUE) {
        DWORD exitCode = 0;
        if (!::GetExitCodeProcess(_current_process, &exitCode)) {
            // invalid handle
            ::CloseHandle(_current_process);
        } else {
            if (exitCode == STILL_ACTIVE) {
                // shut down ohm process
                ::TerminateProcess(_current_process, 0);
            }
            ::CloseHandle(_current_process);
        }
    }
}

HANDLE dev_null() {
    SECURITY_ATTRIBUTES secattr = {};
    secattr.nLength = sizeof(SECURITY_ATTRIBUTES);
    secattr.lpSecurityDescriptor = NULL;
    secattr.bInheritHandle = TRUE;
    return ::CreateFile(TEXT("nul:"), GENERIC_READ | GENERIC_WRITE,
                        FILE_SHARE_READ | FILE_SHARE_WRITE, &secattr,
                        OPEN_EXISTING, 0, nullptr);
}

bool OHMMonitor::checkAvailabe() {
    if (!_available) {
        return false;
    }

    if (_current_process != INVALID_HANDLE_VALUE) {
        DWORD exitCode = 0;
        if (!::GetExitCodeProcess(_current_process, &exitCode)) {
            // handle invalid???
            _logger.crashLog("ohm process handle invalid");
            ::CloseHandle(_current_process);
            _current_process = INVALID_HANDLE_VALUE;
        } else {
            if (exitCode != STILL_ACTIVE) {
                _logger.crashLog("OHM process ended with exit code %" PRIudword,
                          exitCode);
                ::CloseHandle(_current_process);
                _current_process = INVALID_HANDLE_VALUE;
            }
        }
    }

    if (_current_process == INVALID_HANDLE_VALUE) {
        STARTUPINFOA si = {};
        si.cb = sizeof(STARTUPINFOA);
        si.dwFlags |= STARTF_USESTDHANDLES;
        si.hStdOutput = si.hStdError = dev_null();

        OnScopeExit close_stdout([&si]() { CloseHandle(si.hStdOutput); });

        PROCESS_INFORMATION pi = {};

        if (!::CreateProcessA(_exe_path.c_str(), nullptr, nullptr, nullptr,
                              TRUE, 0, nullptr, nullptr, &si, &pi)) {
            _logger.crashLog("failed to run %s", _exe_path.c_str());
            return false;
        } else {
            _current_process = pi.hProcess;
            _logger.crashLog("started %s (pid %lu)", _exe_path.c_str(),
                      pi.dwProcessId);
            ::CloseHandle(pi.hThread);
        }
    }
    return true;
}
