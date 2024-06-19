// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/p_perf_counters.h"

#include <numeric>
#include <ranges>
#include <string>

#include "common/wtools.h"
#include "wnx/cfg.h"
#include "wnx/logger.h"

namespace rs = std::ranges;
using namespace std::string_view_literals;

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
    const std::chrono::duration<double> dur =
        std::chrono::system_clock::now().time_since_epoch();

    auto freq = cfg::GetPerformanceFrequency();
    return fmt::format("{:.2f} {} {}\n", dur.count(), key_index, freq);
}

// <<<winperf_something>>>
std::string MakeWinPerfHeader(std::wstring_view prefix,
                              std::wstring_view name) {
    return section::MakeHeader(wtools::ToUtf8(prefix) + "_" +
                               wtools::ToUtf8(name));
}

// retrieve the next line from a Windows Registry MULTI_SZ registry value
// returns nullptr
const wchar_t *GetNextMultiSz(const std::vector<wchar_t> &data,
                              size_t &offset) {
    if (data.size() < offset + 1) {
        return nullptr;
    }

    const auto *str = &data[offset];
    const auto len = wcslen(str);
    if (len == 0 ||                                      // end of data
        offset + len * sizeof(wchar_t) > data.size()) {  // corrupted
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
    const auto names = wtools::perf::GenerateInstanceNames(perf_object);
    for (auto name : names) {
        rs::replace(name, L' ', L'_');
        out += ' ';
        out += wtools::ToUtf8(name);
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
    wtools::perf::DataSequence result;  // must be local
    key_index = 0;

    // block to separate a s function
    auto index = tools::ConvertToUint32(key);
    if (index.has_value()) {
        result = wtools::perf::ReadPerformanceDataFromRegistry(key);
        if (result.len_ == 0) {
            XLOG::d.t("Obtained no data from counter {}", wtools::ToUtf8(key));
            return {};
        }

    } else {
        // attempt to get named parameter
        XLOG::t("Key Index {} is not found, looking in registry",
                wtools::ToUtf8(key));
        index = wtools::perf::FindPerfIndexInRegistry(key);
        if (!index.has_value()) {
            XLOG::d.t("Key value cannot be processed '{}'",
                      wtools::ToUtf8(key));
            return {};
        }

        result = wtools::perf::ReadPerformanceDataFromRegistry(
            std::to_wstring(index.value()));
    }

    key_index = index.value();  // must be available

    return result;
}

// build Checkmk formatted list of counters
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

    const auto instances = perf::GenerateInstances(perf_object);
    const PERF_COUNTER_BLOCK *block = nullptr;

    std::string accu;
    for (const auto &counter : perf::GenerateCounters(perf_object, block)) {
        auto first_column = static_cast<int>(counter->CounterNameTitleIndex);
        // this logic is strange, but this is as in LWA
        // 1. Index
        first_column -= static_cast<int>(key_index);
        accu += std::to_string(first_column);

        // 2. Value(s)
        if (instances.empty()) {
            accu += ' ';
            accu += std::to_string(perf::GetValueFromBlock(*counter, block));
        } else {
            for (const auto value : perf::GenerateValues(*counter, instances)) {
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

namespace {
std::optional<wtools::AdapterInfo> FindAdapterInfo(
    const wtools::AdapterInfoStore &store, const std::wstring &name) {
    if (const auto search = store.find(name); search != store.end()) {
        return {search->second};
    }

    XLOG::t("IF {} not found", wtools::ToUtf8(name));
    for (auto &&adapter_info : store | rs::views::values) {
        if (name == adapter_info.friendly_name) {
            XLOG::t("IF {} found by friendly name", wtools::ToUtf8(name));
            return {adapter_info};
        }
    }

    return {};
}
}  // namespace

template <typename T>
std::string AddRow(const std::vector<std::wstring> &names,
                   const wtools::AdapterInfoStore &store,
                   const std::wstring_view counter_name,
                   std::function<T(const wtools::AdapterInfo &)> get_value,
                   T default_value) {
    std::vector<std::wstring> values;
    values.reserve(names.size() + 2);
    values.emplace_back(counter_name);
    for (auto &&name : names) {
        const auto adapter_info = FindAdapterInfo(store, name);
        if (adapter_info.has_value()) {
            values.emplace_back(wtools::ConvertToUtf16(
                fmt::format("{}", get_value(*adapter_info))));
        } else {
            const auto default_value_as_string =
                wtools::ConvertToUtf16(fmt::format("{}", default_value));
            values.emplace_back(default_value_as_string);
        }
    }
    values.emplace_back(winperf::if_state_pseudo_counter_type);
    return wtools::ToUtf8(
        std::accumulate(std::next(values.begin()), values.end(), values[0],
                        [](const std::wstring &a, const std::wstring &b) {
                            return a + L' ' + b;
                        }));
}

// builds a section
// empty string on error
// Also this is good example how to use our Perf API
std::string BuildWinPerfSection(std::wstring_view prefix,
                                std::wstring_view name, std::wstring_view key) {
    // read counter into temp structure
    // Attention: data block read have to be available during processing
    uint32_t key_index = 0;
    const auto result = details::LoadWinPerfData(std::wstring(key), key_index);

    const auto *object = wtools::perf::FindPerfObject(result, key_index);
    if (object == nullptr) {
        XLOG::d("Winperf Object name '{}' index [{}] is not found",
                wtools::ToUtf8(key), key_index);
        return {};
    }

    // now we have data and we are building body

    std::string accu;
    // header <<<winperf_?????>>>
    accu += details::MakeWinPerfHeader(prefix, name);

    // time
    // "12345859645.9 8154 232234566"
    accu += details::MakeWinPerfStamp(key_index);
    // names line
    accu += details::MakeWinPerfInstancesLine(object);
    // naked list
    accu += details::MakeWinPerfNakedList(object, key_index);

    if (name == winperf::if_section_name) {
        const auto store = wtools::GetAdapterInfoStore();
        if (store.empty()) {
            XLOG::d("No adapters found");
        }
        const auto names = wtools::perf::GenerateInstanceNames(object);

        accu += AddRow<int>(
                    names, store, winperf::if_state_pseudo_counter,
                    [](const wtools::AdapterInfo &info) -> int {
                        return static_cast<int>(info.oper_status);
                    },
                    static_cast<int>(IF_OPER_STATUS::IfOperStatusUp)) +
                '\n';
        accu += AddRow<std::string>(
                    names, store, winperf::if_mac_pseudo_counter,
                    [](const wtools::AdapterInfo &info) -> std::string {
                        return info.mac_address;
                    },
                    "0") +
                '\n';
    }

    return accu;
}

}  // namespace cma::provider
