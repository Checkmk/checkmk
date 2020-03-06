// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// small helper function to dynamically load api function.
// This can be used for functions that may not exist in windows versions
// we still support

#include "WinApiInterface.h"
#include "types.h"

template <typename FuncT>
FuncT dynamic_func(LPCWSTR dllName, LPCSTR funcName,
                   const WinApiInterface &winapi) {
    HModuleHandle mod{winapi.LoadLibraryW(dllName), winapi};
    if (mod) {
        FARPROC proc = winapi.GetProcAddress(mod.get(), funcName);
        if (proc != nullptr) {
            return (FuncT)proc;
        }
    }
    return nullptr;
}

// There are two macros to declare a dynamic function. The first requires
// the caller to provide the function signature as OriginalFunctionName_type
// the second variant uses c++11 decltype to deduce the type automatically.
//
// The latter is obviously neater at the call site but in case of windows
// apis it requires us to include the header with macros set up such that
// the function get declared. In this case the developers have to take care
// they don't use the functions directly

#define DYNAMIC_FUNC(funcName, dllName, winapi) \
    dynamic_func<funcName_type>(dllName, funcName, winapi)

#define DYNAMIC_FUNC_DECL(func, dllName, winapi) \
    dynamic_func<decltype(&func)>(dllName, #func, winapi)
