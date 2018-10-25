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
