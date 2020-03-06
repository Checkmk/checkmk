// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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

using StringList = std::vector<std::wstring>;

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
