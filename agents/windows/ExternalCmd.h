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

#ifndef ExternalCmd_h
#define ExternalCmd_h

#include <windows.h>
#include "types.h"

class LoggerAdaptor;

class ExternalCmd {
public:
    ExternalCmd(const char *cmdline, const LoggerAdaptor &logger);

    ~ExternalCmd();

    void terminateJob(DWORD exit_code);

    DWORD exitCode();

    DWORD stdoutAvailable();

    DWORD stderrAvailable();

    void closeScriptHandles();

    DWORD readStdout(char *buffer, size_t buffer_size, bool block = true);

    DWORD readStderr(char *buffer, size_t buffer_size, bool block = true);

private:
    DWORD readPipe(HANDLE pipe, char *buffer, size_t buffer_size, bool block);

private:
    WinHandle _script_stderr{INVALID_HANDLE_VALUE};
    WinHandle _script_stdout{INVALID_HANDLE_VALUE};
    HANDLE _process{INVALID_HANDLE_VALUE};
    HANDLE _job_object{INVALID_HANDLE_VALUE};
    WinHandle _stdout{INVALID_HANDLE_VALUE};
    WinHandle _stderr{INVALID_HANDLE_VALUE};
    const LoggerAdaptor &_logger;
};

#endif  // ExternalCmd_h
