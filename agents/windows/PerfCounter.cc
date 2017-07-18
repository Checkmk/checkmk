#include "PerfCounter.h"
#include <tchar.h>
#include <windows.h>
#include <cstdio>
#include <stdexcept>
#include <vector>
#include "PerfCounterCommon.h"
#include "stringutil.h"

// Helper functions to navigate the performance counter data

PERF_OBJECT_TYPE *FirstObject(PERF_DATA_BLOCK *dataBlock) {
    return (PERF_OBJECT_TYPE *)((BYTE *)dataBlock + dataBlock->HeaderLength);
}

PERF_OBJECT_TYPE *NextObject(PERF_OBJECT_TYPE *act) {
    return (PERF_OBJECT_TYPE *)((BYTE *)act + act->TotalByteLength);
}

PERF_COUNTER_DEFINITION *FirstCounter(PERF_OBJECT_TYPE *perfObject) {
    return (PERF_COUNTER_DEFINITION *)((BYTE *)perfObject +
                                       perfObject->HeaderLength);
}

PERF_COUNTER_DEFINITION *NextCounter(PERF_COUNTER_DEFINITION *perfCounter) {
    return (PERF_COUNTER_DEFINITION *)((BYTE *)perfCounter +
                                       perfCounter->ByteLength);
}

PERF_COUNTER_BLOCK *GetCounterBlock(PERF_INSTANCE_DEFINITION *pInstance) {
    return (PERF_COUNTER_BLOCK *)((BYTE *)pInstance + pInstance->ByteLength);
}

PERF_INSTANCE_DEFINITION *FirstInstance(PERF_OBJECT_TYPE *pObject) {
    return (PERF_INSTANCE_DEFINITION *)((BYTE *)pObject +
                                        pObject->DefinitionLength);
}

PERF_INSTANCE_DEFINITION *NextInstance(PERF_INSTANCE_DEFINITION *pInstance) {
    return (PERF_INSTANCE_DEFINITION *)((BYTE *)pInstance +
                                        pInstance->ByteLength +
                                        GetCounterBlock(pInstance)->ByteLength);
}

PerfCounter::PerfCounter(PERF_COUNTER_DEFINITION *counter, BYTE *datablock)
    : _counter(counter), _datablock(datablock) {}

std::string PerfCounter::typeName() const {
    switch (_counter->CounterType) {
        case PERF_COUNTER_COUNTER:
            return "counter";
        case PERF_COUNTER_TIMER:
            return "timer";
        case PERF_COUNTER_QUEUELEN_TYPE:
            return "queuelen_type";
        case PERF_COUNTER_BULK_COUNT:
            return "bulk_count";
        case PERF_COUNTER_TEXT:
            return "text";
        case PERF_COUNTER_RAWCOUNT:
            return "rawcount";
        case PERF_COUNTER_LARGE_RAWCOUNT:
            return "large_rawcount";
        case PERF_COUNTER_RAWCOUNT_HEX:
            return "rawcount_hex";
        case PERF_COUNTER_LARGE_RAWCOUNT_HEX:
            return "large_rawcount_HEX";
        case PERF_SAMPLE_FRACTION:
            return "sample_fraction";
        case PERF_SAMPLE_COUNTER:
            return "sample_counter";
        case PERF_COUNTER_NODATA:
            return "nodata";
        case PERF_COUNTER_TIMER_INV:
            return "timer_inv";
        case PERF_SAMPLE_BASE:
            return "sample_base";
        case PERF_AVERAGE_TIMER:
            return "average_timer";
        case PERF_AVERAGE_BASE:
            return "average_base";
        case PERF_AVERAGE_BULK:
            return "average_bulk";
        case PERF_100NSEC_TIMER:
            return "100nsec_timer";
        case PERF_100NSEC_TIMER_INV:
            return "100nsec_timer_inv";
        case PERF_COUNTER_MULTI_TIMER:
            return "multi_timer";
        case PERF_COUNTER_MULTI_TIMER_INV:
            return "multi_timer_inV";
        case PERF_COUNTER_MULTI_BASE:
            return "multi_base";
        case PERF_100NSEC_MULTI_TIMER:
            return "100nsec_multi_timer";
        case PERF_100NSEC_MULTI_TIMER_INV:
            return "100nsec_multi_timer_inV";
        case PERF_RAW_FRACTION:
            return "raw_fraction";
        case PERF_RAW_BASE:
            return "raw_base";
        case PERF_ELAPSED_TIME:
            return "elapsed_time";
        default: {
            std::ostringstream str;
            str << "type(" << std::hex << _counter->CounterType << ")";
            return str.str();
        } break;
    }
}

ULONGLONG PerfCounter::extractValue(PERF_COUNTER_BLOCK *block) const {
    unsigned offset = _counter->CounterOffset;
    BYTE *pData = ((BYTE *)block) + offset;

    static const DWORD PERF_SIZE_MASK = 0x00000300;

    switch (_counter->CounterType & PERF_SIZE_MASK) {
        case PERF_SIZE_DWORD:
            return static_cast<ULONGLONG>(*(DWORD *)pData);
        case PERF_SIZE_LARGE:
            return *(UNALIGNED ULONGLONG *)pData;
        case PERF_SIZE_ZERO:
            return 0ULL;
        default: {  // PERF_SIZE_VARIABLE_LEN
            // handle other data generically. This is wrong in some situation.
            // Once upon a time in future we might implement a conversion as
            // described in
            // http://msdn.microsoft.com/en-us/library/aa373178%28v=vs.85%29.aspx
            int size = _counter->CounterSize;
            if (size == 4) {
                return static_cast<ULONGLONG>(*(DWORD *)pData);
            } else if (size == 8) {
                DWORD *data_at = (DWORD *)pData;
                return (DWORDLONG)*data_at +
                       ((DWORDLONG) * (data_at + 1) << 32);
            } else {
                return 0ULL;
            }
        } break;
    }
}

std::vector<ULONGLONG> PerfCounter::values(
    const std::vector<PERF_INSTANCE_DEFINITION *> &instances) const {
    std::vector<ULONGLONG> result;
    if (_datablock != NULL) {
        // instanceless counter - instances should be empty
        PERF_COUNTER_BLOCK *counterBlock = (PERF_COUNTER_BLOCK *)_datablock;
        result.push_back(extractValue(counterBlock));
    } else {
        for (PERF_INSTANCE_DEFINITION *instance : instances) {
            PERF_COUNTER_BLOCK *counterBlock = GetCounterBlock(instance);
            result.push_back(extractValue(counterBlock));
        }
    }
    return result;
}

DWORD PerfCounter::titleIndex() const {
    return _counter->CounterNameTitleIndex;
}

DWORD PerfCounter::offset() const { return _counter->CounterOffset; }

static const size_t DEFAULT_BUFFER_SIZE = 40960L;

std::vector<BYTE> PerfCounterObject::retrieveCounterData(
    const wchar_t *counterList) {
    std::vector<BYTE> result;
    result.resize(DEFAULT_BUFFER_SIZE);

    DWORD buffer_size = result.size();
    DWORD type{0};
    DWORD ret;

    while ((ret = RegQueryValueExW(HKEY_PERFORMANCE_DATA, counterList, nullptr,
                                   &type, &result[0], &buffer_size)) !=
           ERROR_SUCCESS) {
        if (ret == ERROR_MORE_DATA) {
            // the size of performance counter blocks is varible and may change
            // concurrently, so there is no way to ensure the buffer is large
            // enough before the call, we can only increase the buffer size
            // until the call succeeds
            buffer_size = result.size() * 2;
            result.resize(buffer_size);
        } else {
            throw std::runtime_error(get_win_error_as_string());
        }
    }

    // apparently this handle is opened on demand by RegQueryValueEx but needs
    // to be closed manually, otherwise we may be blocking installation of apps
    // that create new performance counters.
    // say WHAT???
    RegCloseKey(HKEY_PERFORMANCE_DATA);

    result.resize(buffer_size);
    return result;
}

PerfCounterObject::PerfCounterObject(unsigned int counter_base_number)
    : _datablock(nullptr) {
    _buffer = retrieveCounterData(std::to_wstring(counter_base_number).c_str());

    _object = findObject(counter_base_number);

    std::ostringstream stringStream;
    stringStream << "counter id not found: " << counter_base_number;

    if (_object == NULL) {
        throw std::runtime_error(stringStream.str());
    }

    if (_object->NumInstances <= 0) {
        // set the datablock pointer, but only on an instanceless
        // counter, otherwise it is meaningless
        PERF_COUNTER_DEFINITION *counter = FirstCounter(_object);
        for (DWORD i = 0UL; i < _object->NumCounters; ++i) {
            counter = NextCounter(counter);
        }
        _datablock = (BYTE *)counter;
    }
}

PERF_OBJECT_TYPE *PerfCounterObject::findObject(DWORD counter_index) {
    PERF_DATA_BLOCK *data_block = (PERF_DATA_BLOCK *)&_buffer[0];
    PERF_OBJECT_TYPE *iter = FirstObject(data_block);

    for (DWORD i = 0; i < data_block->NumObjectTypes; ++i) {
        // iterate to the object we requested since apparently there can be more
        // than that in the buffer returned
        if (iter->ObjectNameTitleIndex == counter_index) {
            return iter;
        } else {
            iter = NextObject(iter);
        }
    }
    return NULL;
}

bool PerfCounterObject::isEmpty() const { return _object->NumCounters == 0UL; }

std::vector<PERF_INSTANCE_DEFINITION *> PerfCounterObject::instances() const {
    std::vector<PERF_INSTANCE_DEFINITION *> result;
    if (_object->NumInstances > 0L) {
        PERF_INSTANCE_DEFINITION *instance = FirstInstance(_object);
        for (LONG i = 0L; i < _object->NumInstances; ++i) {
            result.push_back(instance);
            instance = NextInstance(instance);
        }
    }
    return result;
}

std::vector<std::wstring> PerfCounterObject::instanceNames() const {
    std::vector<std::wstring> result;
    if (_object->NumInstances > 0L) {
        PERF_INSTANCE_DEFINITION *instance = FirstInstance(_object);
        for (LONG i = 0L; i < _object->NumInstances; ++i) {
            result.push_back(
                (LPCWSTR)((BYTE *)(instance) + instance->NameOffset));
            instance = NextInstance(instance);
        }
    }
    return result;
}

std::vector<PerfCounter> PerfCounterObject::counters() const {
    std::vector<PerfCounter> result;
    PERF_COUNTER_DEFINITION *counter = FirstCounter(_object);
    for (DWORD i = 0UL; i < _object->NumCounters; ++i) {
        result.push_back(PerfCounter(counter, _datablock));
        counter = NextCounter(counter);
    }
    return result;
}

std::vector<std::wstring> PerfCounterObject::counterNames() const {
    std::map<DWORD, std::wstring> name_map = perf_id_map(false);

    std::vector<std::wstring> result;
    PERF_COUNTER_DEFINITION *counter = FirstCounter(_object);
    for (DWORD i = 0UL; i < _object->NumCounters; ++i) {
        auto iter = name_map.find(counter->CounterNameTitleIndex);
        if (iter != name_map.end()) {
            result.push_back(iter->second);
        } else {
            result.push_back(std::to_wstring(counter->CounterNameTitleIndex));
        }
        counter = NextCounter(counter);
    }
    return result;
}

std::map<DWORD, std::wstring> name_map(const char *language) {
    std::map<DWORD, std::wstring> output;

    HKEY hKey;
    LONG result = RegOpenKeyEx(
        HKEY_LOCAL_MACHINE,
        (std::string(
             "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Perflib\\") +
         language)
            .c_str(),
        REG_MULTI_SZ, KEY_READ, &hKey);

    // preflight
    std::vector<wchar_t> szValueName;
    DWORD dwcbData = 0;
    RegQueryValueExW(hKey, L"Counter", nullptr, nullptr,
                     (LPBYTE)&szValueName[0], &dwcbData);
    szValueName.resize(dwcbData);
    // actual read op
    RegQueryValueExW(hKey, L"Counter", nullptr, nullptr,
                     (LPBYTE)&szValueName[0], &dwcbData);
    RegCloseKey(hKey);
    if (result == ERROR_SUCCESS) {
        size_t offset = 0;
        for (;;) {
            LPCWSTR id = get_next_multi_sz(szValueName, offset);
            LPCWSTR name = get_next_multi_sz(szValueName, offset);
            if ((id == nullptr) || (name == nullptr)) {
                break;
            }
            output[wcstol(id, nullptr, 10)] = name;
        }
    }

    return output;
}

PerfCounterObject::CounterList PerfCounterObject::object_list(
    const char *language) {
    CounterList result;

    std::map<DWORD, std::wstring> name_lookup = name_map(language);

    std::vector<BYTE> counter_data = retrieveCounterData(L"Global");

    PERF_DATA_BLOCK *data_block = (PERF_DATA_BLOCK *)&counter_data[0];
    PERF_OBJECT_TYPE *iter = FirstObject(data_block);

    for (DWORD i = 0; i < data_block->NumObjectTypes; ++i) {
        auto name_iter = name_lookup.find(iter->ObjectNameTitleIndex);
        if (name_iter != name_lookup.end()) {
            result.push_back(
                std::make_pair(iter->ObjectNameTitleIndex, name_iter->second));
        }
        iter = NextObject(iter);
    }

    return result;
}

int PerfCounterObject::resolve_counter_name(const wchar_t *counter_name,
                                            const wchar_t *language) {
    if (language == NULL) {
        // "autodetect", which means we try local language and english
        int result = resolve_counter_name(counter_name, L"CurrentLanguage");
        if (result == -1) {
            result = resolve_counter_name(counter_name, L"009");
        }
        return result;
    } else {
        HKEY hKey;
        LONG result =
            RegOpenKeyExW(HKEY_LOCAL_MACHINE,
                          (std::wstring(L"SOFTWARE\\Microsoft\\Windows "
                                        L"NT\\CurrentVersion\\Perflib\\") +
                           language)
                              .c_str(),
                          REG_MULTI_SZ, KEY_READ, &hKey);

        // preflight
        std::vector<wchar_t> szValueName;
        DWORD dwcbData = 0;
        RegQueryValueExW(hKey, L"Counter", NULL, NULL, (LPBYTE)&szValueName[0],
                         &dwcbData);
        szValueName.resize(dwcbData);
        // actual read op
        RegQueryValueExW(hKey, L"Counter", NULL, NULL, (LPBYTE)&szValueName[0],
                         &dwcbData);
        RegCloseKey(hKey);

        if (result != ERROR_SUCCESS) {
            return -1;
        }

        size_t offset = 0;
        for (;;) {
            const wchar_t *id = get_next_multi_sz(szValueName, offset);
            const wchar_t *name = get_next_multi_sz(szValueName, offset);
            if ((id == NULL) || (name == NULL)) {
                break;
            }
            if (wcscmp(name, counter_name) == 0) {
                return wcstol(id, NULL, 10);
            }
        }

        return -1;
    }
}

int PerfCounterObject::resolve_counter_name(const char *counter_name,
                                            const char *language) {
    if (language == NULL) {
        // "autodetect", which means we try local language and english
        int result = resolve_counter_name(counter_name, "CurrentLanguage");
        if (result == -1) {
            result = resolve_counter_name(counter_name, "009");
        }
        return result;
    } else {
        HKEY hKey;
        LONG result = RegOpenKeyEx(
            HKEY_LOCAL_MACHINE,
            (std::string(
                 "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Perflib\\") +
             language)
                .c_str(),
            REG_MULTI_SZ, KEY_READ, &hKey);

        // preflight
        std::vector<TCHAR> szValueName;
        DWORD dwcbData = 0;
        RegQueryValueEx(hKey, "Counter", NULL, NULL, (LPBYTE)&szValueName[0],
                        &dwcbData);
        szValueName.resize(dwcbData);
        // actual read op
        RegQueryValueEx(hKey, "Counter", NULL, NULL, (LPBYTE)&szValueName[0],
                        &dwcbData);
        RegCloseKey(hKey);

        if (result != ERROR_SUCCESS) {
            return -1;
        }

        size_t offset = 0;
        for (;;) {
            const TCHAR *id = get_next_multi_sz(szValueName, offset);
            const TCHAR *name = get_next_multi_sz(szValueName, offset);
            if ((id == NULL) || (name == NULL)) {
                break;
            }
            if (_tcscmp(name, counter_name) == 0) {
                return _tcstol(id, NULL, 10);
            }
        }

        return -1;
    }
}
