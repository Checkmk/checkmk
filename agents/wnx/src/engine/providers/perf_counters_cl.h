// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

// provides high level api to get perf counters using command line

#pragma once
#ifndef PERF_COUNTERS_CL_H
#define PERF_COUNTERS_CL_H

#include <string>
#include <string_view>
#include <vector>

namespace cma {

namespace provider {

// workhorse of execution
int RunPerf(
    const std::wstring &peer_name,  // name assigned by starting program
    const std::wstring &port,       // format as in carrier.h mail:*
    const std::wstring &answer_id,  // answer id, should be a number
    int /*timeout*/,                // how long wait for execution
    const std::vector<std::wstring_view> &counter_array  // name of counters
);

// internal procedure to get all data from all counters and format for CMK
std::string AccumulateCounters(
    std::wstring_view prefix_name,
    const std::vector<std::wstring_view> &counter_array);

}  // namespace provider

}  // namespace cma

#endif  // PERF_COUNTERS_CL_H
