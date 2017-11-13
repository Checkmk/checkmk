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

#ifndef PerfCounter_h
#define PerfCounter_h

#include <string>
#include <vector>
#include "WinApiAdaptor.h"

typedef uint64_t ULONGLONG;

typedef struct _PERF_COUNTER_DEFINITION PERF_COUNTER_DEFINITION;
typedef struct _PERF_INSTANCE_DEFINITION PERF_INSTANCE_DEFINITION;
typedef struct _PERF_COUNTER_BLOCK PERF_COUNTER_BLOCK;
typedef struct _PERF_OBJECT_TYPE PERF_OBJECT_TYPE;

class Logger;

// Wrapper for a single counter
// Attention: objects of this type become invalid when
//   the corresponding PerfCounterObject is destroyed
class PerfCounter {
    friend class PerfCounterObject;

    PERF_COUNTER_DEFINITION *_counter;
    BYTE *_datablock;  // pointer to where the counter data is stored
                       // If the counter has instances we don't need this
                       // as the instance definition contains a pointer to
                       // the instance-specific data
    const WinApiAdaptor &_winapi;

public:
    std::string typeName() const;
    std::vector<ULONGLONG> values(
        const std::vector<PERF_INSTANCE_DEFINITION *> &instances) const;
    DWORD titleIndex() const;
    DWORD offset() const;

private:
    PerfCounter(PERF_COUNTER_DEFINITION *counter, BYTE *datablock,
                const WinApiAdaptor &winapi);
    ULONGLONG extractValue(PERF_COUNTER_BLOCK *block) const;
};

// Wrapper to deal with performance counters.
// Documentation is here:
// http://msdn.microsoft.com/en-us/library/aa373178(VS.85).aspx
class PerfCounterObject {
    std::vector<BYTE> _buffer;
    PERF_OBJECT_TYPE *_object;
    BYTE *_datablock;
    const WinApiAdaptor &_winapi;
    Logger *_logger;

public:
    typedef std::vector<std::pair<DWORD, std::wstring>> CounterList;

public:
    PerfCounterObject(unsigned counter_base_number, const WinApiAdaptor &winapi,
                      Logger *logger);

    bool isEmpty() const;

    std::vector<PERF_INSTANCE_DEFINITION *> instances() const;
    std::vector<std::wstring> instanceNames() const;
    std::vector<PerfCounter> counters() const;
    std::vector<std::wstring> counterNames() const;

private:
    std::vector<BYTE> retrieveCounterData(const wchar_t *counterList);

    PERF_OBJECT_TYPE *findObject(DWORD counter_index);
};

#endif  // PerfCounter_h
