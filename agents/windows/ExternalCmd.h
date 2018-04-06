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

#include "types.h"

class Environment;
class Logger;
class WinApiInterface;

using PipeHandle = WrappedHandle<InvalidHandleTraits>;

class AgentUpdaterError : public std::runtime_error {
public:
    explicit AgentUpdaterError(const std::string &what)
        : std::runtime_error(buildSectionCheckMK(what)) {}

private:
    std::string buildSectionCheckMK(const std::string &what) const;
};

class ExternalCmd {
    using ProcessHandle = WrappedHandle<NullHandleTraits>;

public:
    ExternalCmd(const std::string &cmdline, const Environment &env,
                Logger *logger, const WinApiInterface &winapi);

    ~ExternalCmd();

    DWORD exitCode();

    DWORD stdoutAvailable();

    DWORD stderrAvailable();

    void closeScriptHandles();

    DWORD readStdout(char *buffer, size_t buffer_size, bool block = true);

    DWORD readStderr(char *buffer, size_t buffer_size, bool block = true);

private:
    DWORD readPipe(HANDLE pipe, char *buffer, size_t buffer_size, bool block);

    PipeHandle _script_stderr;
    PipeHandle _script_stdout;
    ProcessHandle _process;
    JobHandle<1> _job_object;
    PipeHandle _stdout;
    PipeHandle _stderr;
    const bool _with_stderr;
    Logger *_logger;
    const WinApiInterface &_winapi;
};

#endif  // ExternalCmd_h
