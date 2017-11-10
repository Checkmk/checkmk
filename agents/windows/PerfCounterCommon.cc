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

#include "PerfCounterCommon.h"
#include <cstring>
#include <map>
#include <vector>
#include "WinApiAdaptor.h"

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
long regQueryValueEx<wchar_t>(const WinApiAdaptor &winapi, HKEY hkey, const wchar_t *name, LPBYTE result, DWORD *counters_size) {
    return winapi.RegQueryValueExW(hkey, name, nullptr, nullptr, result, counters_size);
}

template <>
long regQueryValueEx<char>(const WinApiAdaptor &winapi, HKEY hkey, const char *name, LPBYTE result, DWORD *counters_size) {
    return winapi.RegQueryValueEx(hkey, name, nullptr, nullptr, result, counters_size);
}
