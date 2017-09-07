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

#ifndef CrashHandler_h
#define CrashHandler_h

#include <string>

#ifndef WINAPI

#if defined(_WIN32) || defined(_WIN64)
#define WINAPI __attribute__((__stdcall__))
#else
#define WINAPI
#endif  // _WIN32 || _WIN64

#endif  // WINAPI

typedef long LONG;
typedef void *PVOID;

#if defined(_WIN64)
typedef int64_t LONG_PTR;
#else
typedef long LONG_PTR;
#endif

typedef struct _EXCEPTION_POINTERS *LPEXCEPTION_POINTERS;
typedef struct _CONTEXT CONTEXT;

class Logger;
class WinApiAdaptor;

class CrashHandler {
    Logger *_logger;
    const WinApiAdaptor &_winapi;

public:
    CrashHandler(Logger *logger, const WinApiAdaptor &winapi);
    CrashHandler(const CrashHandler &) = delete;
    CrashHandler &operator=(const CrashHandler &) = delete;

    LONG WINAPI handleCrash(LPEXCEPTION_POINTERS ptrs) const;

private:
#ifdef __x86_64
    void logBacktrace(PVOID exc_address) const;
#endif  // __x86_64
};

#endif  // CrashHandler_h
