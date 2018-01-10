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

namespace {

HANDLE dev_null(const WinApiAdaptor &winapi) {
    SECURITY_ATTRIBUTES secattr{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    return winapi.CreateFile("nul:", GENERIC_READ | GENERIC_WRITE,
                             FILE_SHARE_READ | FILE_SHARE_WRITE, &secattr,
                             OPEN_EXISTING, 0, nullptr);
}

}  // namespace

OHMMonitor::OHMMonitor(const std::string &bin_path, Logger *logger,
                       const WinApiAdaptor &winapi)
    : _exe_path(bin_path + "\\OpenHardwareMonitorCLI.exe")
    , _available(winapi.GetFileAttributes(_exe_path.c_str()) !=
                 INVALID_FILE_ATTRIBUTES)
    , _current_process(winapi)
    , _logger(logger)
    , _winapi(winapi) {}

OHMMonitor::~OHMMonitor() {}

bool OHMMonitor::startProcess() {
    if (!_available) {
        return false;
    }

    if (_current_process) {
        DWORD exitCode = STILL_ACTIVE;
        if (!_winapi.GetExitCodeProcess(_current_process.get(), &exitCode) ||
            exitCode != STILL_ACTIVE) {
            if (exitCode != STILL_ACTIVE) {
                Debug(_logger)
                    << "OHM process ended with exit code " << exitCode;
            }
            _current_process = {INVALID_HANDLE_VALUE, _winapi};
        }
    }

    if (!_current_process) {
        STARTUPINFO si{0};
        si.cb = sizeof(STARTUPINFO);
        si.dwFlags |= STARTF_USESTDHANDLES;
        si.hStdOutput = si.hStdError = dev_null(_winapi);
        WrappedHandle<InvalidHandleTraits> fileHandle{si.hStdOutput, _winapi};

        PROCESS_INFORMATION pi{0};

        if (!_winapi.CreateProcess(_exe_path.c_str(), nullptr, nullptr, nullptr,
                                   TRUE, 0, nullptr, nullptr, &si, &pi)) {
            Error(_logger) << "failed to run %s" << _exe_path;
            return false;
        } else {
            _current_process = {pi.hProcess, _winapi};
            Debug(_logger) << "started " << _exe_path << " (pid "
                           << pi.dwProcessId << ")";
            WrappedHandle<NullHandleTraits> threadHandle{pi.hThread, _winapi};
        }
    }

    return true;
}
