// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides basic api to start and stop service

#pragma once
#ifndef perf_cpuload_h__
#define perf_cpuload_h__

#include <string>
#include <string_view>

#include "providers/internal.h"
#include "section_header.h"

namespace cma {

namespace provider {

class PerfCpuLoad : public Synchronous {
public:
    static constexpr char kSepChar = '|';
    PerfCpuLoad() : Synchronous(kWmiCpuLoad, kSepChar) {}

private:
    std::string makeBody() override;
    std::unordered_map<std::string, std::string> computer_info_cache_;
};

constexpr std::wstring_view kProcessorQueueLength{
    L"\\System\\Processor Queue Length"};
bool CheckSingleCounter(std::wstring_view path);

}  // namespace provider

};  // namespace cma

#endif  // perf_cpuload_h__
