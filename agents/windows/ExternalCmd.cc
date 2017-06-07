// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

#include "ExternalCmd.h"
#include <memory>
#include "Environment.h"
#include "logging.h"
#include "types.h"

extern bool with_stderr;
extern HANDLE g_workers_job_object;


bool ends_with(std::string const & value, std::string const & ending)
{
    if (ending.size() > value.size()) return false;
    return std::equal(ending.rbegin(), ending.rend(), value.rbegin());
}


ExternalCmd::ExternalCmd(const char *cmdline) {
    SECURITY_DESCRIPTOR security_descriptor;
    SECURITY_ATTRIBUTES security_attributes;
    // initialize security descriptor (Windows NT)
    if (Environment::isWinNt()) {
        InitializeSecurityDescriptor(&security_descriptor,
                                     SECURITY_DESCRIPTOR_REVISION);
        SetSecurityDescriptorDacl(&security_descriptor, true, nullptr, false);
        security_attributes.lpSecurityDescriptor = &security_descriptor;
    } else {
        security_attributes.lpSecurityDescriptor = nullptr;
    }

    security_attributes.nLength = sizeof(SECURITY_ATTRIBUTES);
    // child process needs to be able to inherit the pipe handles
    security_attributes.bInheritHandle = true;

    if (!CreatePipe(&_stdout, &_script_stdout, &security_attributes, 0)) {
        throw win_exception("failed to create pipe");
    }

    if (with_stderr) {
        if (!CreatePipe(&_stderr, &_script_stderr, &security_attributes, 0)) {
            throw win_exception("failed to create pipe");
        }
    }

    // base new process statup info on current process
    STARTUPINFO si;
    ZeroMemory(&si, sizeof(STARTUPINFO));
    si.cb = sizeof(STARTUPINFO);
    GetStartupInfo(&si);
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = _script_stdout;
    si.hStdError = with_stderr ? _script_stdout : _script_stderr;

    PROCESS_INFORMATION pi;
    ZeroMemory(&pi, sizeof(PROCESS_INFORMATION));
    std::unique_ptr<char[], decltype(free) *> cmdline_buf(strdup(cmdline),
                                                          free);

    bool detach_process = ends_with(std::string(cmdline), std::string("cmk-update-agent.exe\""));

    DWORD dwCreationFlags = CREATE_NEW_CONSOLE;
    if (detach_process) {
        crash_log("Detaching process: %s, %d", cmdline, detach_process);
        dwCreationFlags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS;
    }

    if (!CreateProcess(nullptr, cmdline_buf.get(), nullptr, nullptr, TRUE,
                       dwCreationFlags, nullptr, nullptr, &si, &pi)) {
        throw win_exception(std::string("failed to spawn process ") + cmdline);
    }

    _process = pi.hProcess;
    ::CloseHandle(pi.hThread);

    // Create a job object for this process
    // Whenever the process ends all of its childs will terminate, too
    _job_object = CreateJobObject(nullptr, nullptr);
    if (!detach_process) {
      AssignProcessToJobObject(_job_object, pi.hProcess);
      AssignProcessToJobObject(g_workers_job_object, pi.hProcess);
    }
}

ExternalCmd::~ExternalCmd() {
    ::CloseHandle(_stdout);
    ::CloseHandle(_stderr);
    if (_job_object != INVALID_HANDLE_VALUE) {
        ::TerminateJobObject(_job_object, 1);
        ::CloseHandle(_job_object);
    }
    ::CloseHandle(_process);
}

void ExternalCmd::terminateJob(DWORD exit_code) {
    ::TerminateJobObject(_job_object, exit_code);
    ::CloseHandle(_job_object);
    _job_object = INVALID_HANDLE_VALUE;
}

void ExternalCmd::closeScriptHandles() {
    ::CloseHandle(_script_stderr);
    ::CloseHandle(_script_stdout);
}

DWORD ExternalCmd::exitCode() {
    DWORD res;
    GetExitCodeProcess(_process, &res);
    return res;
}

DWORD ExternalCmd::stdoutAvailable() {
    DWORD available;
    PeekNamedPipe(_stdout, nullptr, 0, nullptr, &available, nullptr);
    return available;
}

DWORD ExternalCmd::stderrAvailable() {
    DWORD available;
    PeekNamedPipe(_stderr, nullptr, 0, nullptr, &available, nullptr);
    return available;
}

DWORD ExternalCmd::readStdout(char *buffer, size_t buffer_size, bool block) {
    return readPipe(_stdout, buffer, buffer_size, block);
}

DWORD ExternalCmd::readStderr(char *buffer, size_t buffer_size, bool block) {
    if (!with_stderr) {
        return readPipe(_stderr, buffer, buffer_size, block);
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
        PeekNamedPipe(pipe, nullptr, 0, nullptr, &available, nullptr);
    }
    if (available > 0) {
        ReadFile(pipe, buffer, std::min<DWORD>(available, buffer_size - 1),
                 &bytes_read, nullptr);
        buffer[bytes_read] = '\0';
    }
    return bytes_read;
}
