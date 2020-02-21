// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef CrashHandler_h
#define CrashHandler_h

#include <string>

#ifndef WINAPI

#if defined(_WIN32) || defined(_WIN64)
#if defined(_MSC_BUILD)
#define WINAPI __stdcall
#else
#define WINAPI __attribute__((__stdcall__))
#endif
#else
#define WINAPI
#endif  // _WIN32 || _WIN64

#endif  // WINAPI

using LPEXCEPTION_POINTERS = struct _EXCEPTION_POINTERS *;
using CONTEXT = struct _CONTEXT;

class Logger;
class WinApiInterface;

class CrashHandler {
public:
    CrashHandler(Logger *logger, const WinApiInterface &winapi);
    CrashHandler(const CrashHandler &) = delete;
    CrashHandler &operator=(const CrashHandler &) = delete;

    long WINAPI handleCrash(LPEXCEPTION_POINTERS ptrs) const;

private:
#ifdef __x86_64
    void logBacktrace(void *exc_address) const;
#endif  // __x86_64

    Logger *_logger;
    const WinApiInterface &_winapi;
};

#endif  // CrashHandler_h
