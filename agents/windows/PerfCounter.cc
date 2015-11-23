#include "PerfCounter.h"
#include "stringutil.h"
#include <windows.h>
#include <vector>
#include <cstdio>
#include <stdexcept>


extern void verbose(const char *format, ...) __attribute__ ((format (gnu_printf, 1, 2)));
extern void crash_log(const char *format, ...) __attribute__ ((format (gnu_printf, 1, 2)));


// Helper functions to navigate the performance counter data

PERF_OBJECT_TYPE *FirstObject(PERF_DATA_BLOCK *dataBlock) {
    return (PERF_OBJECT_TYPE *) ((BYTE *)dataBlock + dataBlock->HeaderLength);
}


PERF_OBJECT_TYPE *NextObject(PERF_OBJECT_TYPE *act) {
    return (PERF_OBJECT_TYPE *) ((BYTE *)act + act->TotalByteLength);
}


PERF_COUNTER_DEFINITION *FirstCounter(PERF_OBJECT_TYPE *perfObject) {
    return (PERF_COUNTER_DEFINITION *) ((BYTE *) perfObject + perfObject->HeaderLength);
}


PERF_COUNTER_DEFINITION *NextCounter(PERF_COUNTER_DEFINITION *perfCounter) {
    return (PERF_COUNTER_DEFINITION *) ((BYTE *) perfCounter + perfCounter->ByteLength);
}


PERF_COUNTER_BLOCK *GetCounterBlock(PERF_INSTANCE_DEFINITION *pInstance) {
    return (PERF_COUNTER_BLOCK *) ((BYTE *)pInstance + pInstance->ByteLength);
}


PERF_INSTANCE_DEFINITION *FirstInstance (PERF_OBJECT_TYPE *pObject) {
    return (PERF_INSTANCE_DEFINITION *)  ((BYTE *) pObject + pObject->DefinitionLength);
}


PERF_INSTANCE_DEFINITION *NextInstance (PERF_INSTANCE_DEFINITION *pInstance) {
    return (PERF_INSTANCE_DEFINITION *) ((BYTE *)pInstance + pInstance->ByteLength + GetCounterBlock(pInstance)->ByteLength);
}



PerfCounter::PerfCounter(PERF_COUNTER_DEFINITION *counter, BYTE *datablock)
    : _counter(counter)
    , _datablock(datablock)
{
}


std::string PerfCounter::typeName() const
{
    switch (_counter->CounterType) {
        case PERF_COUNTER_COUNTER:            return "counter";
        case PERF_COUNTER_TIMER:              return "timer";
        case PERF_COUNTER_QUEUELEN_TYPE:      return "queuelen_type";
        case PERF_COUNTER_BULK_COUNT:         return "bulk_count";
        case PERF_COUNTER_TEXT:               return "text";
        case PERF_COUNTER_RAWCOUNT:           return "rawcount";
        case PERF_COUNTER_LARGE_RAWCOUNT:     return "large_rawcount";
        case PERF_COUNTER_RAWCOUNT_HEX:       return "rawcount_hex";
        case PERF_COUNTER_LARGE_RAWCOUNT_HEX: return "large_rawcount_HEX";
        case PERF_SAMPLE_FRACTION:            return "sample_fraction";
        case PERF_SAMPLE_COUNTER:             return "sample_counter";
        case PERF_COUNTER_NODATA:             return "nodata";
        case PERF_COUNTER_TIMER_INV:          return "timer_inv";
        case PERF_SAMPLE_BASE:                return "sample_base";
        case PERF_AVERAGE_TIMER:              return "average_timer";
        case PERF_AVERAGE_BASE:               return "average_base";
        case PERF_AVERAGE_BULK:               return "average_bulk";
        case PERF_100NSEC_TIMER:              return "100nsec_timer";
        case PERF_100NSEC_TIMER_INV:          return "100nsec_timer_inv";
        case PERF_COUNTER_MULTI_TIMER:        return "multi_timer";
        case PERF_COUNTER_MULTI_TIMER_INV:    return "multi_timer_inV";
        case PERF_COUNTER_MULTI_BASE:         return "multi_base";
        case PERF_100NSEC_MULTI_TIMER:        return "100nsec_multi_timer";
        case PERF_100NSEC_MULTI_TIMER_INV:    return "100nsec_multi_timer_inV";
        case PERF_RAW_FRACTION:               return "raw_fraction";
        case PERF_RAW_BASE:                   return "raw_base";
        case PERF_ELAPSED_TIME:               return "elapsed_time";
        default: {
                     std::ostringstream str;
                     str << "type(" << std::hex << _counter->CounterType << ")";
                     return str.str();
                 } break;

    }
}


ULONGLONG PerfCounter::extractValue(PERF_COUNTER_BLOCK *block) const
{
    unsigned offset = _counter->CounterOffset;
    int size        = _counter->CounterSize;
    BYTE *pData     = ((BYTE *)block) + offset;

    if (_counter->CounterType & PERF_SIZE_DWORD) {
        return static_cast<ULONGLONG>(*(DWORD*)block);
    }
    else if (_counter->CounterType & PERF_SIZE_LARGE) {
        return *(UNALIGNED ULONGLONG*)pData;
    }
    // handle other data generically. This is wrong in some situation.
    // Once upon a time in future we might implement a conversion as
    // described in http://msdn.microsoft.com/en-us/library/aa373178%28v=vs.85%29.aspx
    else if (size == 4) {
        return static_cast<ULONGLONG>(*(DWORD*)pData);
    }
    else if (size == 8) {
        DWORD *data_at = (DWORD *)pData;
        return (DWORDLONG)*data_at + ((DWORDLONG)*(data_at + 1) << 32);
    }
    else {
        return 0ULL;
    }
}


std::vector<ULONGLONG> PerfCounter::values(const std::vector<PERF_INSTANCE_DEFINITION*> &instances) const
{
    std::vector<ULONGLONG> result;
    if (_datablock != NULL) {
        // instanceless counter - instances should be empty
        PERF_COUNTER_BLOCK *counterBlock = (PERF_COUNTER_BLOCK *) _datablock;
        result.push_back(extractValue(counterBlock));
    } else {
        for (PERF_INSTANCE_DEFINITION *instance : instances) {
            PERF_COUNTER_BLOCK *counterBlock = GetCounterBlock(instance);
            result.push_back(extractValue(counterBlock));
        }
    }
    return result;
}


DWORD PerfCounter::titleIndex() const
{
    return _counter->CounterNameTitleIndex;
}


DWORD PerfCounter::offset() const
{
    return _counter->CounterOffset;
}


static const size_t DEFAULT_BUFFER_SIZE = 40960L;


PerfCounterObject::PerfCounterObject(unsigned int counter_base_number)
    : _buffer(DEFAULT_BUFFER_SIZE)
    , _datablock(NULL)
{
    DWORD buffer_size = _buffer.size();
    DWORD type;
    DWORD ret;

    while ((ret = RegQueryValueEx(HKEY_PERFORMANCE_DATA, std::to_string(counter_base_number).c_str(),
                NULL, &type, &_buffer[0], &buffer_size)) != ERROR_SUCCESS) {
        if (ret == ERROR_MORE_DATA) {
            // the size of performance counter blocks is varible and may change concurrently,
            // so there is no way to ensure the buffer is large enough before the call, we
            // can only increase the buffer size until the call succeeds
            verbose("Buffer for RegQueryValueEx too small. Resizing...");
            buffer_size = _buffer.size() * 2;
            _buffer.resize(buffer_size);
        } else {
            throw std::runtime_error(get_win_error_as_string());
        }
    }

    // apparently this handle is opened on demand by RegQueryValueEx but needs to be
    // closed manually, otherwise we may be blocking installation of apps that create new
    // performance counters.
    // say WHAT???
    RegCloseKey(HKEY_PERFORMANCE_DATA);

    _buffer.resize(buffer_size);

    _object = findObject(counter_base_number);

    if (_object->NumInstances == 0) {
        // set the datablock pointer, but only on an instanceless
        // counter, otherwise it is meaningless
        PERF_COUNTER_DEFINITION *counter = FirstCounter(_object);
        for (DWORD i = 0UL; i < _object->NumCounters; ++i) {
            counter = NextCounter(counter);
        }
        _datablock = (BYTE*)counter;
    }
}


PERF_OBJECT_TYPE *PerfCounterObject::findObject(DWORD counter_index)
{
    PERF_DATA_BLOCK *data_block = (PERF_DATA_BLOCK *)&_buffer[0];
    PERF_OBJECT_TYPE *iter = FirstObject(data_block);

    for (DWORD i = 0; i < data_block->NumObjectTypes; ++i) {
        // iterate to the object we requested since apparently there can be more than
        // that in the buffer returned
        if (iter->ObjectNameTitleIndex == counter_index) {
            return iter;
        } else {
            iter = NextObject(iter);
        }
    }
    return NULL;
}


bool PerfCounterObject::isEmpty() const
{
    return _object->NumCounters == 0UL;
}


std::vector<PERF_INSTANCE_DEFINITION*> PerfCounterObject::instances() const
{
    std::vector<PERF_INSTANCE_DEFINITION*> result;
    if (_object->NumInstances > 0L) {
        PERF_INSTANCE_DEFINITION *instance = FirstInstance(_object);
        for (LONG i = 0L; i < _object->NumInstances; ++i) {
            result.push_back(instance);
            instance = NextInstance(instance);
        }
    }
    return result;
}


std::vector<std::wstring> PerfCounterObject::instanceNames() const
{
    std::vector<std::wstring> result;
    if (_object->NumInstances > 0L) {
        PERF_INSTANCE_DEFINITION *instance = FirstInstance(_object);
        for (LONG i = 0L; i < _object->NumInstances; ++i) {
            result.push_back((LPCWSTR)((BYTE*)(instance) + instance->NameOffset));
            instance = NextInstance(instance);
        }
    }
    return result;
}


std::vector<PerfCounter> PerfCounterObject::counters() const
{
    std::vector<PerfCounter> result;
    PERF_COUNTER_DEFINITION *counter = FirstCounter(_object);
    for (DWORD i = 0UL; i < _object->NumCounters; ++i) {
        result.push_back(PerfCounter(counter, _datablock));
        counter = NextCounter(counter);
    }
    return result;
}

