// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#pragma once
#ifndef P_PERF_COUNTERS_H
#define P_PERF_COUNTERS_H

#include <string>
#include <string_view>

#include "providers/internal.h"
#include "wnx/section_header.h"

namespace cma::provider {
class UptimeSync : public Synchronous {
public:
    UptimeSync() noexcept : Synchronous(section::kUptimeName, 0) {}

    UptimeSync(const std::string &name, char separator) noexcept
        : Synchronous(name, separator) {}

    explicit UptimeSync(const std::string &name) noexcept
        : Synchronous(name, 0) {}

protected:
    std::string makeBody() override;
};

class UptimeAsync : public Asynchronous {
public:
    UptimeAsync() noexcept : Asynchronous(section::kUptimeName, 0) {}

    UptimeAsync(const std::string &name, char separator) noexcept
        : Asynchronous(name, separator) {}

    explicit UptimeAsync(const std::string &name) noexcept
        : Asynchronous(name, 0) {}

protected:
    std::string makeBody() override;
};

namespace winperf {
constexpr std::wstring_view if_section_name = L"if";
constexpr std::wstring_view if_state_pseudo_counter = L"2002";
constexpr std::wstring_view if_state_pseudo_counter_type = L"text";
constexpr std::wstring_view if_mac_pseudo_counter = L"2006";
constexpr std::wstring_view if_mac_pseudo_counter_type = L"text";
}  // namespace winperf

// probably should go in another namespace(used also by skype)
namespace details {
// low level registry scanners
wtools::perf::DataSequence LoadWinPerfData(const std::wstring &key,
                                           uint32_t &key_index);

// first line
std::string MakeWinPerfStamp(uint32_t key_index);
// header
std::string MakeWinPerfHeader(std::wstring_view prefix, std::wstring_view name);
std::string MakeWinPerfNakedList(const PERF_OBJECT_TYPE *perf_object,
                                 uint32_t key_index);
}  // namespace details

std::string BuildWinPerfSection(std::wstring_view prefix,
                                std::wstring_view name, std::wstring_view key);

}  // namespace cma::provider

#endif  // P_PERF_COUNTERS_H
