// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#pragma once

#include <winsock2.h>
#include <windows.h>
#include <string>
#include "types.h"

class Logger;
class WinApiInterface;

struct OhmProcessHandleTraits {
    using HandleT = HANDLE;
    static HandleT invalidValue() { return INVALID_HANDLE_VALUE; }

    static void closeHandle(HandleT value, const WinApiInterface &winapi) {
        DWORD exitCode = 0;
        if (winapi.GetExitCodeProcess(value, &exitCode) &&
            exitCode == STILL_ACTIVE) {
            // shut down ohm process
            winapi.TerminateProcess(value, 0);
        }
        winapi.CloseHandle(value);
    }
};

using OhmProcessHandle = WrappedHandle<OhmProcessHandleTraits>;

class OHMMonitor {
    const std::string _exe_path;
    const bool _available;
    OhmProcessHandle _current_process;
    Logger *_logger;
    const WinApiInterface &_winapi;

public:
    OHMMonitor(const std::string &bin_path, Logger *logger,
               const WinApiInterface &winapi);
    ~OHMMonitor();

    /**
     * Ensure the Open Hardware Monitor is running (if it's available).
     * Return true if it was already running or was successfully started.
     **/
    bool startProcess();
};
