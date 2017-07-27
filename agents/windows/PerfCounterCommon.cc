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

static std::vector<wchar_t> retrieve_perf_data(const WinApiAdaptor &winapi,
                                               LPCWSTR name, bool local) {
    std::vector<wchar_t> result;
    DWORD counters_size = 0;

    HKEY key = local ? HKEY_PERFORMANCE_NLSTEXT : HKEY_PERFORMANCE_TEXT;

    // preflight
    winapi.RegQueryValueExW(key, name, nullptr, nullptr, (LPBYTE)&result[0],
                            &counters_size);

    result.resize(counters_size);
    // actual read op
    winapi.RegQueryValueExW(key, name, nullptr, nullptr, (LPBYTE)&result[0],
                            &counters_size);

    return result;
}

std::map<DWORD, std::wstring> perf_id_map(const WinApiAdaptor &winapi,
                                          bool local) {
    std::vector<wchar_t> names = retrieve_perf_data(winapi, L"Counter", local);

    std::map<DWORD, std::wstring> result;

    size_t offset = 0;
    for (;;) {
        LPCWSTR id = get_next_multi_sz(names, offset);
        LPCWSTR name = get_next_multi_sz(names, offset);
        if ((id == nullptr) || (name == nullptr)) {
            break;
        }

        result[wcstol(id, nullptr, 10)] = name;
    }

    return result;
}

std::map<std::wstring, DWORD> perf_name_map(const WinApiAdaptor &winapi,
                                            bool local) {
    std::vector<wchar_t> names = retrieve_perf_data(winapi, L"Counter", local);

    std::map<std::wstring, DWORD> result;

    size_t offset = 0;
    for (;;) {
        LPCWSTR id = get_next_multi_sz(names, offset);
        LPCWSTR name = get_next_multi_sz(names, offset);
        if ((id == nullptr) || (name == nullptr)) {
            break;
        }

        result[name] = wcstol(id, nullptr, 10);
    }

    return result;
}
