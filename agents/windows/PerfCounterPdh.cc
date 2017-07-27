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

#include "PerfCounterPdh.h"
#include <pdhmsg.h>
#include <stdio.h>
#include <ctime>
#include <sstream>
#include "PerfCounterCommon.h"
#include "win_error.h"

std::wstring resolve_perf_id(int id) {
    std::wstring result;
    DWORD buffer_size = 0;

    PDH_STATUS status =
        PdhLookupPerfNameByIndexW(nullptr, id, &result[0], &buffer_size);
    if ((DWORD)status == PDH_MORE_DATA) {
        result.resize(buffer_size);
        status =
            PdhLookupPerfNameByIndexW(nullptr, id, &result[0], &buffer_size);
    }

    if ((DWORD)status != ERROR_SUCCESS) {
        throw std::runtime_error(get_win_error_as_string(status));
    }
    return result;
}

PerfCounterQuery::PerfCounterQuery() {
    PDH_STATUS status = PdhOpenQuery(nullptr, 0, &_query);
    if (status != ERROR_SUCCESS) {
        std::ostringstream err;
        err << "open query failed with 0x" << std::hex << status;
        throw std::runtime_error(err.str());
    }

    _perf_name_index = perf_name_map(false);
    std::map<DWORD, std::wstring> local_perf_names = perf_id_map(true);

    for (const auto &name_id : _perf_name_index) {
        auto local_iter = local_perf_names.find(name_id.second);
        if (local_iter != local_perf_names.end()) {
            _translation_map[local_iter->second] = name_id.first;
        }
    }
}

PerfCounterQuery::~PerfCounterQuery() { PdhCloseQuery(_query); }

HCOUNTER PerfCounterQuery::addCounter(const std::wstring &path) {
    auto iter = _counter.find(path);
    if (iter != _counter.end()) {
        return iter->second;
    } else {
        HCOUNTER counter;
        PDH_STATUS status = PdhAddCounterW(_query, path.c_str(), 0, &counter);
        if (status != ERROR_SUCCESS) {
            printf("add counter status: %lx\n", (DWORD)status);
            throw std::runtime_error(get_win_error_as_string(status));
        }
        return counter;
    }
}

std::wstring PerfCounterQuery::makePath(const std::wstring &object,
                                        const std::wstring instance,
                                        const std::wstring &counter) {
    std::wostringstream result;
    result << "\\" << object << "(" << instance << ")"
           << "\\" << counter;
    return result.str();
}

std::pair<StringList, StringList> PerfCounterQuery::enumerateObject(
    LPCWSTR object_name_in) const {
    std::wstring counterlist_buffer;
    std::wstring instancelist_buffer;

    DWORD counterlist_size = 0;
    DWORD instancelist_size = 0;

    std::wstring object_name(object_name_in);

    PDH_STATUS status = PdhEnumObjectItemsW(
        nullptr, nullptr, object_name.c_str(), &counterlist_buffer[0],
        &counterlist_size, &instancelist_buffer[0], &instancelist_size,
        PERF_DETAIL_WIZARD, 0);

    if ((DWORD)status == PDH_CSTATUS_NO_OBJECT) {
        // maybe the name is in english?
        auto iter = _perf_name_index.find(object_name);
        if (iter != _perf_name_index.end()) {
            // bingo. resolve that name to local language
            // and continue with that
            object_name = resolve_perf_id(iter->second);
            status = PdhEnumObjectItemsW(
                nullptr, nullptr, object_name.c_str(), &counterlist_buffer[0],
                &counterlist_size, &instancelist_buffer[0], &instancelist_size,
                PERF_DETAIL_WIZARD, 0);
        }
    }

    if ((DWORD)status == ERROR_SUCCESS) {
        // our buffer size was 0. If the call does NOT ask for more buffer,
        // there obviously is no such performance counter
        return std::make_pair(StringList(), StringList());
    } else if ((DWORD)status != PDH_MORE_DATA) {
        throw std::runtime_error(get_win_error_as_string(status));
    }

    // Allocate the buffers and try the call again.
    counterlist_buffer.resize(counterlist_size);
    instancelist_buffer.resize(instancelist_size);

    status = PdhEnumObjectItemsW(nullptr, nullptr, object_name.c_str(),
                                 &counterlist_buffer[0], &counterlist_size,
                                 &instancelist_buffer[0], &instancelist_size,
                                 PERF_DETAIL_WIZARD, 0);

    if (status != ERROR_SUCCESS) {
        throw std::runtime_error(get_win_error_as_string(status));
    }

    StringList counterlist;

    // the buffer contains a zero-terminted list of zero-terminated strings
    for (LPCWSTR iter = &counterlist_buffer[0]; *iter != L'\0';
         iter += wcslen(iter) + 1) {
        counterlist.push_back(iter);
        /*        auto translation = _translation_map.find(iter);
                if (translation != _translation_map.end()) {
                    counterlist.push_back(translation->second);
                } else {
                    counterlist.push_back(iter);
                }*/
    }

    StringList instancelist;

    for (LPCWSTR iter = &instancelist_buffer[0]; *iter != L'\0';
         iter += wcslen(iter) + 1) {
        instancelist.push_back(iter);
    }

    return std::make_pair(counterlist, instancelist);
}

StringList PerfCounterQuery::enumerateObjects() const {
    std::vector<wchar_t> buffer;
    DWORD buffer_size = 0;

    // this call can take several seconds, as it refreshes the whole list of
    // performance counters
    PDH_STATUS status = PdhEnumObjectsW(nullptr, nullptr, &buffer[0],
                                        &buffer_size, PERF_DETAIL_WIZARD, TRUE);

    if ((DWORD)status == PDH_MORE_DATA) {
        // documentation says to add 1 to the buffer size on winxp.
        ++buffer_size;
        buffer.resize(buffer_size);
        status = PdhEnumObjectsW(nullptr, nullptr, &buffer[0], &buffer_size,
                                 PERF_DETAIL_WIZARD, FALSE);
    }

    StringList result;
    if (status == ERROR_SUCCESS) {
        size_t offset = 0;
        for (;;) {
            LPCWSTR name = get_next_multi_sz(buffer, offset);
            if (name == nullptr) {
                break;
            } else {
                result.push_back(name);
            }
        }

        return result;
    } else {
        throw std::runtime_error(get_win_error_as_string(status));
    }
}

void PerfCounterQuery::execute() {
    PDH_STATUS status = PdhCollectQueryData(_query);

    if (((DWORD)status != ERROR_SUCCESS) &&
        ((DWORD)status != PDH_NO_MORE_DATA)) {
        throw std::runtime_error(get_win_error_as_string(status));
    }
}

std::wstring PerfCounterQuery::counterValue(LPCWSTR name) const {
    auto iter = _counter.find(name);
    if (iter == _counter.end()) {
        throw std::runtime_error("invalid counter name");
    }

    return counterValue(iter->second);
}

std::wstring type_name(DWORD type_id) {
    switch (type_id) {
        case PERF_COUNTER_COUNTER:
            return L"counter";
        case PERF_COUNTER_TIMER:
            return L"timer";
        case PERF_COUNTER_QUEUELEN_TYPE:
            return L"queuelen_type";
        case PERF_COUNTER_BULK_COUNT:
            return L"bulk_count";
        case PERF_COUNTER_TEXT:
            return L"text";
        case PERF_COUNTER_RAWCOUNT:
            return L"rawcount";
        case PERF_COUNTER_LARGE_RAWCOUNT:
            return L"large_rawcount";
        case PERF_COUNTER_RAWCOUNT_HEX:
            return L"rawcount_hex";
        case PERF_COUNTER_LARGE_RAWCOUNT_HEX:
            return L"large_rawcount_HEX";
        case PERF_SAMPLE_FRACTION:
            return L"sample_fraction";
        case PERF_SAMPLE_COUNTER:
            return L"sample_counter";
        case PERF_COUNTER_NODATA:
            return L"nodata";
        case PERF_COUNTER_TIMER_INV:
            return L"timer_inv";
        case PERF_SAMPLE_BASE:
            return L"sample_base";
        case PERF_AVERAGE_TIMER:
            return L"average_timer";
        case PERF_AVERAGE_BASE:
            return L"average_base";
        case PERF_AVERAGE_BULK:
            return L"average_bulk";
        case PERF_100NSEC_TIMER:
            return L"100nsec_timer";
        case PERF_100NSEC_TIMER_INV:
            return L"100nsec_timer_inv";
        case PERF_COUNTER_MULTI_TIMER:
            return L"multi_timer";
        case PERF_COUNTER_MULTI_TIMER_INV:
            return L"multi_timer_inV";
        case PERF_COUNTER_MULTI_BASE:
            return L"multi_base";
        case PERF_100NSEC_MULTI_TIMER:
            return L"100nsec_multi_timer";
        case PERF_100NSEC_MULTI_TIMER_INV:
            return L"100nsec_multi_timer_inV";
        case PERF_RAW_FRACTION:
            return L"raw_fraction";
        case PERF_RAW_BASE:
            return L"raw_base";
        case PERF_ELAPSED_TIME:
            return L"elapsed_time";
        default: {
            std::wostringstream str;
            str << L"type(" << std::hex << type_id << L")";
            return str.str();
        } break;
    }
}

std::wstring PerfCounterQuery::counterValue(HCOUNTER counter) const {
    DWORD type;
    PDH_RAW_COUNTER value;

    PDH_STATUS status = PdhGetRawCounterValue(counter, &type, &value);

    if (status != ERROR_SUCCESS) {
        throw std::runtime_error(get_win_error_as_string(status));
    }

    std::wostringstream str;

    str << value.FirstValue << "," << value.SecondValue << ","
        << value.MultiCount << "," << type_name(type);

    return str.str();
}

std::wstring PerfCounterQuery::trans(const std::wstring &local_name) const {
    auto iter = _translation_map.find(local_name);
    if (iter != _translation_map.end()) {
        return iter->second;
    } else {
        return local_name;
    }
}
