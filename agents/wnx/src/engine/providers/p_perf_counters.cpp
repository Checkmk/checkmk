
// provides basic api to start and stop service
#include "stdafx.h"

#include "providers/p_perf_counters.h"

#include <iostream>
#include <string>

#include "cfg.h"
#include "common/wtools.h"
#include "logger.h"
#include "tools/_raii.h"

namespace cma {

namespace provider {

std::string UptimeSync::makeBody() {
    auto count = GetTickCount64();
    count /= 1000;  // time in milliseconds
    std::string s = std::to_string(count);
    return s;
}

std::string UptimeAsync::makeBody() {
    auto count = GetTickCount64();
    count /= 1000;  // time in milliseconds
    std::string s = std::to_string(count);
    return s;
}

namespace details {
// returns string
// "<seconds since epoch> <KeyIndex> <frequency>\n"
// Example:
// "1548673688.07 510 2156253\n"
std::string MakeWinPerfStamp(uint32_t KeyIndex) {
    using namespace std::chrono;

    // time is seconds default as double
    duration<double> dur = system_clock::now().time_since_epoch();

    auto freq = cma::cfg::GetPerformanceFrequency();
    return fmt::format("{:.2f} {} {}\n", dur.count(), KeyIndex, freq);
}

// <<<winperf_something>>>
std::string MakeWinPerfHeader(std::wstring_view prefix,
                              std::wstring_view name) {
    auto name_string = wtools::ConvertToUTF8(name);

    return cma::section::MakeHeader(wtools::ConvertToUTF8(prefix) + "_" +
                                    name_string);
}

// retrieve the next line from a Windows Registry MULTI_SZ registry value
// returns nullptr
const wchar_t* GetNextMultiSz(const std::vector<wchar_t>& Data,
                              size_t& Offset) {
    if (Data.size() < Offset + 1) return nullptr;  // sanity check

    auto str = &Data[Offset];
    auto len = wcslen(str);

    if ((len == 0) ||  // end of data
        (Offset + (len * sizeof(wchar_t)) >
         Data.size())) {  // registry is corrupted
        return nullptr;
    }

    Offset += len + 1;
    return str;
}

std::string MakeWinPerfInstancesLine(const PERF_OBJECT_TYPE* Object) {
    if (Object && Object->NumInstances > 0) {
        // this is as in 'LWA'
        // negative count is skipped
        std::string out = std::to_string(Object->NumInstances) + " instances:";
        auto names = wtools::perf::GenerateInstanceNames(Object);
        for (auto name : names) {
            std::replace(name.begin(), name.end(), L' ', L'_');
            auto name_of_instance = wtools::ConvertToUTF8(name);
            out += ' ';
            out += name_of_instance;
        }
        out += '\n';
        return out;
    }

    return {};
}

// Determines valid key
// Reads data and deliver it back
// empty data is error
// KeyIndex is set to 0 on start
wtools::perf::DataSequence LoadWinPerfData(const std::wstring& Key,
                                           uint32_t& KeyIndex) {
    using namespace wtools;
    perf::DataSequence result;  // must be local
    KeyIndex = 0;

    // block to separate a s function
    auto ret = cma::tools::ConvertToUint32(Key);
    if (ret.has_value()) {
        result = wtools::perf::ReadPerformanceDataFromRegistry(Key);
        if (result.len_ == 0) {
            XLOG::t.t("Obtained no data from counter {}", ConvertToUTF8(Key));
            return {};
        }

    } else {
        // attempt to get named parameter
        XLOG::t("Key Index {} is not found, looking in registry",
                wtools::ConvertToUTF8(Key));
        ret = wtools::perf::FindPerfIndexInRegistry(Key);
        if (!ret.has_value()) {
            XLOG::t.t("Key value cannot be processed '{}'", ConvertToUTF8(Key));
            return {};
        }

        result = wtools::perf::ReadPerformanceDataFromRegistry(
            std::to_wstring(ret.value()));
    }

    // read registry
    KeyIndex = ret.value();  // must be available

    return std::move(result);
}

// build Check MK formatted list of counters
// Instance less support too
// Empty string on error
std::string MakeWinPerfNakedList(const PERF_OBJECT_TYPE* Object,
                                 uint32_t KeyIndex) {
    using namespace wtools;

    if (Object == nullptr) {
        XLOG::t("Object is null for index [{}]", KeyIndex);
        return {};
    }

    auto instances = perf::GenerateInstances(Object);
    const PERF_COUNTER_BLOCK* block = nullptr;
    auto counters = perf::GenerateCounters(Object, block);

    std::string accu;
    for (const auto& counter : counters) {
        int first_column = counter->CounterNameTitleIndex;
        // this logic is strange, but this is as in LWA
        // 1. Index
        first_column -= static_cast<int>(KeyIndex);
        accu += std::to_string(first_column);

        // 2. Value(s)
        if (instances.size() > 0) {
            auto values = perf::GenerateValues(*counter, instances);

            for (auto value : values) {
                accu += ' ';
                accu += std::to_string(value);
            }
        } else {
            auto value = perf::GetValueFromBlock(*counter, block);
            accu += ' ';
            accu += std::to_string(value);
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
    using namespace std;
    using namespace wtools;

    // read counter into temp structure
    // Attention: data block read have to be available during processing
    uint32_t key_index = 0;
    auto result = details::LoadWinPerfData(std::wstring(key), key_index);

    auto object = wtools::perf::FindPerfObject(result, key_index);
    if (!object) return {};

    // now we have data and we are building body

    string accu;
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

}  // namespace provider
};  // namespace cma
