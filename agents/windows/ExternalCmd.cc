// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "ExternalCmd.h"
#include <shlwapi.h>
#include <cstring>
#include "Environment.h"
#include "Logger.h"
#include "WinApiInterface.h"
#include "win_error.h"

namespace {

const char *updater_exe = "cmk-update-agent.exe";

bool ends_with(std::string const &value, std::string const &ending) {
    if (ending.size() > value.size()) return false;
    return std::equal(ending.rbegin(), ending.rend(), value.rbegin());
}

std::string combinePaths(const std::string &path1, const std::string &path2,
                         const WinApiInterface &winapi) {
    std::vector<char> combined(MAX_PATH, '\0');
    return winapi.PathCombine(combined.data(), path1.c_str(), path2.c_str());
}

// Prepare cmk-update-agent.exe for being run in temp directory.
std::string handleAgentUpdater(Logger *logger, const WinApiInterface &winapi) {
    const auto *env = Environment::instance();
    if (env == nullptr) {
        const std::string errorMsg = "No environment!";
        Error(logger) << errorMsg;
        throw win_exception(winapi, errorMsg);
    }
    const auto source =
        combinePaths(env->pluginsDirectory(), updater_exe, winapi);
    const auto target = combinePaths(env->tempDirectory(), updater_exe, winapi);

    if (!winapi.CopyFile(source.c_str(), target.c_str(), false)) {
        std::string errorMsg = "copying ";
        errorMsg += source + " to " + target + " failed.";
        Error(logger) << errorMsg;
        throw AgentUpdaterError(errorMsg);
    }

    return target;
}

std::pair<PipeHandle, PipeHandle> createPipe(SECURITY_ATTRIBUTES &attr,
                                             const WinApiInterface &winapi) {
    HANDLE readPipe = INVALID_HANDLE_VALUE;
    HANDLE writePipe = INVALID_HANDLE_VALUE;
    if (!winapi.CreatePipe(&readPipe, &writePipe, &attr, 0)) {
        throw win_exception(winapi, "failed to create pipe");
    }
    return {PipeHandle{readPipe, winapi}, PipeHandle{writePipe, winapi}};
}

}  // namespace

std::string AgentUpdaterError::buildSectionCheckMK(
    const std::string &what) const {
    return "<<<check_mk>>>\nAgentUpdate: last_check None "
           "last_update None aghash None error " +
           what + "\n";
}

ExternalCmd::ExternalCmd(const std::string &cmdline, const Environment &env,
                         Logger *logger, const WinApiInterface &winapi)
    : _script_stderr{winapi}
    , _script_stdout{winapi}
    , _process{winapi}
    , _job_object{winapi}
    , _stdout{winapi}
    , _stderr{winapi}
    , _with_stderr{env.withStderr()}
    , _logger(logger)
    , _winapi(winapi) {
    SECURITY_DESCRIPTOR security_descriptor;
    SECURITY_ATTRIBUTES security_attributes;
    // initialize security descriptor (Windows NT)
    if (env.isWinNt()) {
        _winapi.InitializeSecurityDescriptor(&security_descriptor,
                                             SECURITY_DESCRIPTOR_REVISION);
        _winapi.SetSecurityDescriptorDacl(&security_descriptor, true, nullptr,
                                          false);
        security_attributes.lpSecurityDescriptor = &security_descriptor;
    } else {
        security_attributes.lpSecurityDescriptor = nullptr;
    }

    security_attributes.nLength = sizeof(SECURITY_ATTRIBUTES);
    // child process needs to be able to inherit the pipe handles
    security_attributes.bInheritHandle = true;

    std::tie(_stdout, _script_stdout) =
        createPipe(security_attributes, _winapi);

    if (_with_stderr) {
        std::tie(_stderr, _script_stderr) =
            createPipe(security_attributes, _winapi);
    }

    // base new process statup info on current process
    STARTUPINFO si;
    std::memset(&si, 0, sizeof(STARTUPINFO));
    si.cb = sizeof(STARTUPINFO);
    _winapi.GetStartupInfo(&si);
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = _script_stdout.get();
    si.hStdError = _with_stderr ? _script_stdout.get() : _script_stderr.get();

    bool detach_process = false;
    std::string actualCmd(cmdline);

    if (ends_with(cmdline, std::string(updater_exe) + "\"")) {
        detach_process = true;
        // Prepare cmk-update-agent.exe for being run in temp directory.
        actualCmd = handleAgentUpdater(logger, _winapi);
    }

    std::vector<char> cmdline_buf(actualCmd.cbegin(), actualCmd.cend());
    cmdline_buf.push_back('\0');

    DWORD dwCreationFlags = CREATE_NEW_CONSOLE;
    if (detach_process) {
        Debug(_logger) << "Detaching process: " << actualCmd << ", "
                       << detach_process;
        dwCreationFlags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS;
    }

    PROCESS_INFORMATION pi;
    std::memset(&pi, 0, sizeof(PROCESS_INFORMATION));

    if (!_winapi.CreateProcess(nullptr, cmdline_buf.data(), nullptr, nullptr,
                               TRUE, dwCreationFlags, nullptr, nullptr, &si,
                               &pi)) {
        std::string errorMsg = "failed to spawn process " + actualCmd;
        if (detach_process) {
            throw AgentUpdaterError(errorMsg);
        } else {
            throw win_exception(winapi, errorMsg);
        }
    }

    _process = {pi.hProcess, _winapi};
    ProcessHandle threadHandle{pi.hThread, _winapi};

    // Create a job object for this process
    // Whenever the process ends all of its children will terminate, too
    _job_object = {_winapi.CreateJobObject(nullptr, nullptr), _winapi};
    if (!detach_process) {
        _winapi.AssignProcessToJobObject(_job_object.get(), pi.hProcess);
        _winapi.AssignProcessToJobObject(env.workersJobObject().get(),
                                         pi.hProcess);
    }
}

ExternalCmd::~ExternalCmd() {}

DWORD ExternalCmd::exitCode() {
    DWORD res;
    _winapi.GetExitCodeProcess(_process.get(), &res);
    return res;
}

DWORD ExternalCmd::stdoutAvailable() {
    DWORD available;
    _winapi.PeekNamedPipe(_stdout.get(), nullptr, 0, nullptr, &available,
                          nullptr);
    return available;
}

DWORD ExternalCmd::stderrAvailable() {
    DWORD available;
    _winapi.PeekNamedPipe(_stderr.get(), nullptr, 0, nullptr, &available,
                          nullptr);
    return available;
}

DWORD ExternalCmd::readStdout(char *buffer, size_t buffer_size, bool block) {
    return readPipe(_stdout.get(), buffer, buffer_size, block);
}

DWORD ExternalCmd::readStderr(char *buffer, size_t buffer_size, bool block) {
    if (!_with_stderr) {
        return readPipe(_stderr.get(), buffer, buffer_size, block);
    } else {
        return 0;
    }
}

DWORD ExternalCmd::readPipe(HANDLE pipe, char *buffer, size_t buffer_size,
                            bool block) {
    DWORD bytes_read = 0UL;
    DWORD available = buffer_size;
    if (!block) {
        // avoid blocking by first peeking.
        _winapi.PeekNamedPipe(pipe, nullptr, 0, nullptr, &available, nullptr);
    }
    if (available > 0) {
        _winapi.ReadFile(pipe, buffer,
                         std::min<DWORD>(available, buffer_size - 1),
                         &bytes_read, nullptr);
        buffer[bytes_read] = '\0';
    }
    return bytes_read;
}
