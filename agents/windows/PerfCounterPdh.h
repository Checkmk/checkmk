// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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

#ifndef PerfCounterPdh_h
#define PerfCounterPdh_h

/**
 *
 * Cleaner implementation of Performance counter querying using pdh.dll
 * Not currently used
 *
 */

#define WIN32_LEAN_AND_MEAN
#include <pdh.h>
#include <map>
#include <string>
#include <utility>
#include <vector>

typedef std::vector<std::wstring> StringList;

class PerfCounterQuery {
    HQUERY _query;
    std::map<std::wstring, HCOUNTER> _counter;
    std::map<std::wstring, DWORD> _perf_name_index;
    std::map<std::wstring, std::wstring> _translation_map;

public:
    PerfCounterQuery();

    ~PerfCounterQuery();

    HCOUNTER addCounter(const std::wstring &path);

    static std::wstring makePath(const std::wstring &object,
                                 const std::wstring instance,
                                 const std::wstring &counter);

    // enumerates all counters and instances for the specified object
    std::pair<StringList, StringList> enumerateObject(
        LPCWSTR object_name) const;

    StringList enumerateObjects() const;

    void execute();

    std::wstring counterValue(LPCWSTR name) const;
    std::wstring counterValue(HCOUNTER counter) const;

    std::wstring trans(const std::wstring &local_name) const;
};

#endif  // PerfCounterPdh_h
