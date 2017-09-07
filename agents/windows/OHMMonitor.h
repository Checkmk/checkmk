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

#pragma once

#include <winsock2.h>
#include <windows.h>
#include <string>

class Logger;
class WinApiAdaptor;

/**
 * Ensure the Open Hardware Monitor is running (if it's available)
 **/
class OHMMonitor {
    std::string _exe_path;
    bool _available;
    HANDLE _current_process{INVALID_HANDLE_VALUE};
    Logger *_logger;
    const WinApiAdaptor &_winapi;

public:
    OHMMonitor(const std::string &bin_path, Logger *logger,
               const WinApiAdaptor &winapi);
    ~OHMMonitor();

    // this call actually starts OHM if necessary and returns
    // true if it was already running or was successfully started
    bool checkAvailabe();
};
