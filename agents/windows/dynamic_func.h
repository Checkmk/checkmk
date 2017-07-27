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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

// small helper function to dynamically load api function.
// This can be used for functions that may not exist in windows versions
// we still support

#include "WinApiAdaptor.h"

template <typename FuncT>
FuncT dynamic_func(LPCWSTR dllName, LPCSTR funcName,
                   const WinApiAdaptor &winapi) {
    HMODULE mod = winapi.LoadLibraryW(dllName);
    if (mod != nullptr) {
        FARPROC proc = winapi.GetProcAddress(mod, funcName);
        winapi.CloseHandle(mod);
        if (proc != nullptr) {
            return (FuncT)proc;
        }
    }
    return nullptr;
}

// there are two macros to declare a dynamic function. The first requires the
// caller to provide the function signature as OriginalFunctionName_type
// the second variant uses c++11 decltype to deduce the type automatically.
//
// The latter is obviously neater at the call site but in case of windows apis
// it
// requires us to include the header with macros set up such that the function
// get declared. In this case the developers have to take care they don't use
// the
// functions directly

#define DYNAMIC_FUNC(funcName, dllName, winapi) \
    dynamic_func<funcName_type>(dllName, funcName, winapi)

#define DYNAMIC_FUNC_DECL(func, dllName, winapi) \
    dynamic_func<decltype(&func)>(dllName, #func, winapi)
