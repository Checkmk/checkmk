// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#include "PerfCounterCommon.h"
#include <cstring>
#include <map>
#include <vector>
#include "WinApiInterface.h"

template <>
size_t string_length<char>(const char *s) {
    return strlen(s);
}

template <>
size_t string_length<wchar_t>(const wchar_t *s) {
    return wcslen(s);
}

template <>
const wchar_t *getCounterValueName<wchar_t>() {
    return L"Counter";
}

template <>
const char *getCounterValueName<char>() {
    return "Counter";
}

template <>
long strTolFunc<wchar_t>(const wchar_t *str, wchar_t **str_end, int base) {
    return wcstol(str, str_end, base);
}

template <>
long strTolFunc<char>(const char *str, char **str_end, int base) {
    return strtol(str, str_end, base);
}

template <>
long regQueryValueEx<wchar_t>(const WinApiInterface &winapi, HKEY hkey,
                              const wchar_t *name, LPBYTE result,
                              DWORD *counters_size) {
    return winapi.RegQueryValueExW(hkey, name, nullptr, nullptr, result,
                                   counters_size);
}

template <>
long regQueryValueEx<char>(const WinApiInterface &winapi, HKEY hkey,
                           const char *name, LPBYTE result,
                           DWORD *counters_size) {
    return winapi.RegQueryValueEx(hkey, name, nullptr, nullptr, result,
                                  counters_size);
}
