// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "OHMMonitor.h"
#include "Logger.h"
#include "WinApiInterface.h"

namespace {

HANDLE dev_null(const WinApiInterface &winapi) {
    SECURITY_ATTRIBUTES secattr{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
    return winapi.CreateFile("nul:", GENERIC_READ | GENERIC_WRITE,
                             FILE_SHARE_READ | FILE_SHARE_WRITE, &secattr,
                             OPEN_EXISTING, 0, nullptr);
}

}  // namespace

OHMMonitor::OHMMonitor(const std::string &bin_path, Logger *logger,
                       const WinApiInterface &winapi)
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
