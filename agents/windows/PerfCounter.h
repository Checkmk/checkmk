// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#ifndef PerfCounter_h
#define PerfCounter_h

#include <string>
#include <vector>
#include "WinApiInterface.h"

class Logger;

// Wrapper for a single counter
// Attention: objects of this type become invalid when
//   the corresponding PerfCounterObject is destroyed
class PerfCounter {
    friend class PerfCounterObject;

public:
    std::string typeName() const;
    std::vector<ULONGLONG> values(
        const std::vector<PERF_INSTANCE_DEFINITION *> &instances) const;
    DWORD titleIndex() const;
    DWORD offset() const;

private:
    PerfCounter(PERF_COUNTER_DEFINITION *counter, BYTE *datablock,
                const WinApiInterface &winapi);
    ULONGLONG extractValue(PERF_COUNTER_BLOCK *block) const;

    PERF_COUNTER_DEFINITION *_counter;
    BYTE *_datablock;  // pointer to where the counter data is stored
                       // If the counter has instances we don't need this
                       // as the instance definition contains a pointer to
                       // the instance-specific data
    const WinApiInterface &_winapi;
};

// Wrapper to deal with performance counters.
// Documentation is here:
// http://msdn.microsoft.com/en-us/library/aa373178(VS.85).aspx
class PerfCounterObject {
public:
    using CounterList = std::vector<std::pair<DWORD, std::wstring>>;

    PerfCounterObject(unsigned counter_base_number,
                      const WinApiInterface &winapi, Logger *logger);

    bool isEmpty() const;

    std::vector<PERF_INSTANCE_DEFINITION *> instances() const;
    std::vector<std::wstring> instanceNames() const;
    std::vector<PerfCounter> counters() const;
    std::vector<std::wstring> counterNames() const;

private:
    std::vector<BYTE> retrieveCounterData(const wchar_t *counterList);
    PERF_OBJECT_TYPE *findObject(DWORD counter_index);

    std::vector<BYTE> _buffer;
    PERF_OBJECT_TYPE *_object;
    BYTE *_datablock;
    const WinApiInterface &_winapi;
    Logger *_logger;
};

#endif  // PerfCounter_h
