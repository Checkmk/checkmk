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

#include <map>
#include <vector>

class WinApiAdaptor;
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

// returns a map of performance counter indices to the corresponding names.
// This can be used to resolve fields like CounterNameTitleIndex
// if local is set, localized names are used, otherwise the names are english
std::map<DWORD, std::wstring> perf_id_map(const WinApiAdaptor &winapi,
                                          bool local);

// returns the map inverse to perf_id_map. This is necessary
// when one wants to translate between localized and english counter names
std::map<std::wstring, DWORD> perf_name_map(const WinApiAdaptor &winapi,
                                            bool local);
