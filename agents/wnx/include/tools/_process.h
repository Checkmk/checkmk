// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once

#include <Windows.h>
#include <shlobj.h>

#include <string>
#include <string_view>
#include <tuple>

#include "tools/_raii.h"
#include "tools/_xlog.h"

namespace cma::tools {
inline bool RunCommandAndWait(const std::wstring &command,
                              const std::wstring &work_dir) {
    STARTUPINFOW si{0};
    ::memset(&si, 0, sizeof(si));
    si.cb = sizeof(STARTUPINFO);
    si.dwFlags |= STARTF_USESTDHANDLES;  // SK: not sure with this flag

    PROCESS_INFORMATION pi{nullptr};
    ::memset(&pi, 0, sizeof(pi));
    // CREATE_NEW_CONSOLE

    auto working_folder = work_dir.empty() ? nullptr : work_dir.data();

    if (::CreateProcessW(nullptr,  // stupid windows want null here
                         const_cast<wchar_t *>(command.c_str()),  // win32!
                         nullptr,         // security attribute
                         nullptr,         // thread attribute
                         FALSE,           // no handle inheritance
                         0,               // Creation Flags
                         nullptr,         // environment
                         working_folder,  // current directory
                         &si, &pi)) {
        ::WaitForSingleObject(pi.hProcess, INFINITE);
        ::CloseHandle(pi.hProcess);
        ::CloseHandle(pi.hThread);
        return true;
    }
    return false;
}

inline bool RunCommandAndWait(const std::wstring &command) {
    return RunCommandAndWait(command, L"");
}

inline bool RunDetachedCommand(const std::string &command) {
    STARTUPINFOA si{0};
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(STARTUPINFO);
    si.dwFlags |= STARTF_USESTDHANDLES;  // SK: not sure with this flag

    PROCESS_INFORMATION pi{0};
    memset(&pi, 0, sizeof(pi));
    // CREATE_NEW_CONSOLE

    if (::CreateProcessA(nullptr,  // stupid windows want null here
                         const_cast<char *>(command.c_str()),  // win32!
                         nullptr,  // security attribute
                         nullptr,  // thread attribute
                         FALSE,    // no handle inheritance
                         0,        // Creation Flags
                         nullptr,  // environment
                         nullptr,  // current directory
                         &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        return true;
    }
    return false;
}

// NOTE: LAST and BEST attempt to have standard windows starter
// Returns process id on success
/// IMPORTANT: SET inherit_handle to TRUE may prevent script form start
inline uint32_t RunStdCommand(
    std::wstring_view command,    // full command with arguments
    bool wait_for_end,            // important flag! set false when you are sure
    BOOL inherit_handle = FALSE,  // recommended option
    HANDLE stdio_handle = 0,      // when we want to catch output
    HANDLE stderr_handle = 0,     // same
    DWORD creation_flags = 0,     // never checked this
    DWORD start_flags = 0) {
    // windows "boiler plate"
    STARTUPINFOW si{0};
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(STARTUPINFO);
    si.dwFlags = start_flags;
    si.hStdOutput = stdio_handle;
    si.hStdError = stderr_handle;
    if (inherit_handle)
        si.dwFlags = STARTF_USESTDHANDLES;  // switch to the handles in si

    PROCESS_INFORMATION pi{0};
    memset(&pi, 0, sizeof(pi));

    if (::CreateProcessW(nullptr,  // stupid windows want null here
                         const_cast<wchar_t *>(command.data()),  // win32!
                         nullptr,         // security attribute
                         nullptr,         // thread attribute
                         inherit_handle,  // handle inheritance
                         creation_flags,  // Creation Flags
                         nullptr,         // environment
                         nullptr,         // current directory
                         &si, &pi)) {
        auto process_id = pi.dwProcessId;
        if (wait_for_end) WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        return process_id;
    }
    return 0;
}

// Tree controlling command
// #TODO make right API from this wrapper
// returns [ProcId, JobHandle, ProcessHandle]
inline std::tuple<DWORD, HANDLE, HANDLE> RunStdCommandAsJob(
    const std::wstring &Command,  // full command with arguments
    BOOL inherit_handle = FALSE,  // not optimal, but default
    HANDLE stdio_handle = 0,      // when we want to catch output
    HANDLE stderr_handle = 0,     // same
    DWORD creation_flags = 0,     // never checked this
    DWORD start_flags = 0) noexcept {
    // windows "boiler plate"
    STARTUPINFOW si{0};
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(STARTUPINFO);
    si.dwFlags = start_flags;
    si.hStdOutput = stdio_handle;
    si.hStdError = stderr_handle;
    if (inherit_handle)
        si.dwFlags = STARTF_USESTDHANDLES;  // switch to the handles in si
    PROCESS_INFORMATION pi{0};
    memset(&pi, 0, sizeof(pi));
    // -end-

    auto job_handle = CreateJobObjectA(nullptr, nullptr);

    if (!job_handle) return {0, nullptr, nullptr};

    if (!::CreateProcessW(NULL,  // stupid windows want null here
                          const_cast<wchar_t *>(Command.c_str()),  // win32!
                          nullptr,         // security attribute
                          nullptr,         // thread attribute
                          inherit_handle,  // handle inheritance
                          creation_flags,  // Creation Flags
                          nullptr,         // environment
                          nullptr,         // current directory
                          &si, &pi)) {
        // #TODO diagnostic here!
        // clean out here. No process created
        CloseHandle(job_handle);

        return {0, nullptr, nullptr};
    }

    auto process_id = pi.dwProcessId;
    AssignProcessToJobObject(job_handle, pi.hProcess);

    CloseHandle(pi.hThread);
    return {process_id, job_handle, pi.hProcess};
}

#if defined(_WIN32)

namespace win {
inline bool IsElevated() {
    HANDLE token = NULL;
    if (!::OpenProcessToken(::GetCurrentProcess(), TOKEN_QUERY, &token))
        return false;
    ON_OUT_OF_SCOPE(if (token)::CloseHandle(token););

    TOKEN_ELEVATION elevation;
    DWORD size = sizeof(TOKEN_ELEVATION);
    if (::GetTokenInformation(token, TokenElevation, &elevation,
                              sizeof(elevation), &size)) {
        return elevation.TokenIsElevated == TRUE;
    }
    return false;
}

inline std::wstring GetSomeSystemFolder(const KNOWNFOLDERID &rfid) noexcept {
    wchar_t *str = nullptr;
    if (SHGetKnownFolderPath(rfid, KF_FLAG_DEFAULT, NULL, &str) != S_OK ||
        !str)  // probably impossible case when executed ok, but str is nullptr
        return {};

    std::wstring path = str;
    if (str) CoTaskMemFree(str);  // win32
    return path;
}

inline std::wstring GetSystem32Folder() {
    return GetSomeSystemFolder(FOLDERID_System);
}

inline std::wstring GetTempFolder() {
    wchar_t path[MAX_PATH * 2];
    if (::GetTempPathW(MAX_PATH * 2, path)) {
        return path;
    }

    return L"";
}

}  // namespace win

#endif
}  // namespace cma::tools
