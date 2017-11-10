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

#include <wtypes.h>
#include <unordered_map>
#include <vector>

typedef unsigned long DWORD;

template <typename CharT>
size_t string_length(const CharT *s);

template <>
size_t string_length<char>(const char *s);

template <>
size_t string_length<wchar_t>(const wchar_t *s);

// retrieve the next line from a multi-sz registry key
template <typename CharT>
const CharT *get_next_multi_sz(const std::vector<CharT> &data, size_t &offset) {
    const CharT *next = &data[offset];
    size_t len = string_length(next);
    if ((len == 0) || (offset + (len * sizeof(CharT)) > data.size())) {
        // the second condition would only happen with an invalid registry value
        // but that's not unheard of
        return nullptr;
    } else {
        offset += len + 1;
        return next;
    }
}

template <typename CharT>
inline const CharT *getCounterValueName();

template <>
const wchar_t *getCounterValueName<wchar_t>();

template <>
const char *getCounterValueName<char>();

template <typename CharT>
inline long strTolFunc(const CharT *str, CharT **str_end, int base);

template <>
long strTolFunc<wchar_t>(const wchar_t *str, wchar_t **str_end, int base);

template <>
long strTolFunc<char>(const char *str, char **str_end, int base);

template <typename CharT>
long regQueryValueEx(HKEY hkey, const CharT *name, LPBYTE result,
                     DWORD *counters_size);

template <>
long regQueryValueEx<wchar_t>(HKEY hkey, const wchar_t *name, LPBYTE result,
                              DWORD *counters_size);

template <>
long regQueryValueEx<char>(HKEY hkey, const char *name, LPBYTE result,
                           DWORD *counters_size);

template <typename CharT>
inline std::vector<CharT> retrievePerfCounterNames(const CharT *name,
                                                   bool local) {
    std::vector<CharT> result;
    DWORD counters_size = 0;

    HKEY key = local ? HKEY_PERFORMANCE_NLSTEXT : HKEY_PERFORMANCE_TEXT;

    // preflight
    regQueryValueEx(key, name, (LPBYTE)&result[0], &counters_size);

    result.resize(counters_size);
    // actual read op
    regQueryValueEx(key, name, (LPBYTE)&result[0], &counters_size);

    return result;
}

// Returns a map of performance counter indices to the corresponding names.
// If local is set, localized names are used, otherwise the names are english.
template <typename CharT>
inline std::unordered_map<DWORD, std::basic_string<CharT>> perf_id_map(
    bool local) {
    std::vector<CharT> names =
        retrievePerfCounterNames<CharT>(getCounterValueName<CharT>(), local);

    std::unordered_map<DWORD, std::basic_string<CharT>> result;

    size_t offset = 0;
    for (;;) {
        const CharT *id = get_next_multi_sz(names, offset);
        const CharT *name = get_next_multi_sz(names, offset);
        if ((id == nullptr) || (name == nullptr)) {
            break;
        }

        result[strTolFunc<CharT>(id, nullptr, 10)] = name;
    }

    return result;
}

// Returns a map of performance counter names to the corresponding indices.
// If local is set, localized names are used, otherwise the names are english.
template <typename CharT>
inline std::unordered_map<std::basic_string<CharT>, DWORD> perf_name_map(
    bool local) {
    std::vector<CharT> names =
        retrievePerfCounterNames<CharT>(getCounterValueName<CharT>(), local);

    std::unordered_map<std::basic_string<CharT>, DWORD> result;

    size_t offset = 0;
    for (;;) {
        const CharT *id = get_next_multi_sz(names, offset);
        const CharT *name = get_next_multi_sz(names, offset);
        if ((id == nullptr) || (name == nullptr)) {
            break;
        }

        result[name] = strTolFunc<CharT>(id, nullptr, 10);
    }

    return result;
}

// Resolves the ID of the given performance counter entry based on its name.
// The counter name can be either localized or in english.
template <typename CharT>
int resolveCounterName(const std::basic_string<CharT> &counterName) {
    for (bool local : {true, false}) {
        const auto nameIdMap = perf_name_map<CharT>(local);
        const auto it = nameIdMap.find(counterName);

        if (it != nameIdMap.end()) {
            return it->second;
        }
    }

    return -1;
}
