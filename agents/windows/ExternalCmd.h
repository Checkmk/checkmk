// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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
