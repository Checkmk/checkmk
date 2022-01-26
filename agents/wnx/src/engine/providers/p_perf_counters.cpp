// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/p_perf_counters.h"

#include <iostream>
#include <string>

#include "cfg.h"
#include "common/wtools.h"
#include "logger.h"
#include "tools/_raii.h"

namespace cma::provider {

std::string UptimeSync::makeBody() {
    auto count = ::GetTickCount64();
    count /= 1000;  // time in milliseconds
    return std::to_string(count);
}

std::string UptimeAsync::makeBody() {
    auto count = ::GetTickCount64();
    count /= 1000;  // time in milliseconds
    return std::to_string(count);
}

namespace details {
// returns string
// "<seconds since epoch> <KeyIndex> <frequency>\n"
// Example:
// "1548673688.07 510 2156253\n"
std::string MakeWinPerfStamp(uint32_t key_index) {
    // time is seconds, but as double - requirement from LWA
    std::chrono::duration<double> dur =
        std::chrono::system_clock::now().time_since_epoch();

    auto freq = cma::cfg::GetPerformanceFrequency();
    return fmt::format("{:.2f} {} {}\n", dur.count(), key_index, freq);
}

// <<<winperf_something>>>
std::string MakeWinPerfHeader(std::wstring_view prefix,
                              std::wstring_view name) {
    auto name_string = wtools::ToUtf8(name);

    return cma::section::MakeHeader(wtools::ToUtf8(prefix) + "_" + name_string);
}

// retrieve the next line from a Windows Registry MULTI_SZ registry value
// returns nullptr
const wchar_t *GetNextMultiSz(const std::vector<wchar_t> &data,
                              size_t &offset) {
    if (data.size() < offset + 1) return nullptr;  // sanity check

    const auto *str = &data[offset];
    auto len = wcslen(str);

    if ((len == 0) ||  // end of data
        (offset + (len * sizeof(wchar_t)) >
         data.size())) {  // registry is corrupted
        return nullptr;
    }

    offset += len + 1;
    return str;
}

std::string MakeWinPerfInstancesLine(const PERF_OBJECT_TYPE *perf_object) {
    if (perf_object == nullptr || perf_object->NumInstances <= 0) {
        return {};
    }

    // this is as in 'LWA'
    // negative count is skipped
    std::string out = std::to_string(perf_object->NumInstances) + " instances:";
    auto names = wtools::perf::GenerateInstanceNames(perf_object);
    for (auto name : names) {
        std::replace(name.begin(), name.end(), L' ', L'_');
        auto name_of_instance = wtools::ToUtf8(name);
        out += ' ';
        out += name_of_instance;
    }
    out += '\n';
    return out;
}

// Determines valid key
// Reads data and deliver it back
// empty data is error
// key_index is set to 0 on start
wtools::perf::DataSequence LoadWinPerfData(const std::wstring &key,
                                           uint32_t &key_index) {
    namespace perf = wtools::perf;

    perf::DataSequence result;  // must be local
    key_index = 0;

    // block to separate a s function
    auto ret = cma::tools::ConvertToUint32(key);
    if (ret.has_value()) {
        result = perf::ReadPerformanceDataFromRegistry(key);
        if (result.len_ == 0) {
            XLOG::d.t("Obtained no data from counter {}", wtools::ToUtf8(key));
            return {};
        }

    } else {
        // attempt to get named parameter
        XLOG::t("Key Index {} is not found, looking in registry",
                wtools::ToUtf8(key));
        ret = perf::FindPerfIndexInRegistry(key);
        if (!ret.has_value()) {
            XLOG::d.t("Key value cannot be processed '{}'",
                      wtools::ToUtf8(key));
            return {};
        }

        result =
            perf::ReadPerformanceDataFromRegistry(std::to_wstring(ret.value()));
    }

    // read registry
    key_index = ret.value();  // must be available

    return result;
}

// build Check MK formatted list of counters
// Instance less support too
// Empty string on error
std::string MakeWinPerfNakedList(const PERF_OBJECT_TYPE *perf_object,
                                 uint32_t key_index) {
    namespace perf = wtools::perf;

    if (perf_object == nullptr) {
        // can't happen - still defensive programming for Windows Agent
        XLOG::l.crit("Object is null for index [{}]", key_index);
        return {};
    }

    auto instances = perf::GenerateInstances(perf_object);
    const PERF_COUNTER_BLOCK *block = nullptr;
    auto counters = perf::GenerateCounters(perf_object, block);

    std::string accu;
    for (const auto &counter : counters) {
        int first_column = counter->CounterNameTitleIndex;
        // this logic is strange, but this is as in LWA
        // 1. Index
        first_column -= static_cast<int>(key_index);
        accu += std::to_string(first_column);

        // 2. Value(s)
        if (instances.empty()) {
            auto value = perf::GetValueFromBlock(*counter, block);
            accu += ' ';
            accu += std::to_string(value);
        } else {
            auto values = perf::GenerateValues(*counter, instances);

            for (auto value : values) {
                accu += ' ';
                accu += std::to_string(value);
            }
        }

        // 3 or Last. Name
        accu += ' ';

        accu += perf::GetName(counter->CounterType) + '\n';
    }

    return accu;
}

}  // namespace details

// builds a section
// empty string on error
// Also this is good example how to use our Perf API
std::string BuildWinPerfSection(std::wstring_view prefix,
                                std::wstring_view name, std::wstring_view key) {
    namespace perf = wtools::perf;
    // read counter into temp structure
    // Attention: data block read have to be available during processing
    uint32_t key_index = 0;
    auto result = details::LoadWinPerfData(std::wstring(key), key_index);

    const auto *object = perf::FindPerfObject(result, key_index);
    if (object == nullptr) {
        XLOG::d("Winperf Object name '{}' index [{}] is not found",
                wtools::ToUtf8(key), key_index);
        return {};
    }

    // now we have data and we are building body

    std::string accu;
    // header <<<winperf_?????>>>
    auto header = details::MakeWinPerfHeader(prefix, name);
    accu += header;

    // time
    // "12345859645.9 8154 232234566"
    auto line = details::MakeWinPerfStamp(key_index);
    accu += line;

    // names line
    auto instances_line = details::MakeWinPerfInstancesLine(object);
    accu += instances_line;

    // naked list

    auto list = details::MakeWinPerfNakedList(object, key_index);
    accu += list;

    return accu;
}

}  // namespace cma::provider
