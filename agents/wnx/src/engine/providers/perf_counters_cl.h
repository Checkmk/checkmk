
// provides high level api to get perf counters using command line

#pragma once
#ifndef perf_counters_cl_h__
#define perf_counters_cl_h__

#include <string>
#include <string_view>
#include <vector>

namespace cma {

namespace provider {

// workhorse of execution
int RunPerf(const std::wstring& PeerName,  // name assigned by starting program
            const std::wstring& Port,      // format as in carrier.h mail:*
            const std::wstring& Id,        // answer id, should be a number
            int Timeout,                   // how long wait for execution
            std::vector<std::wstring_view> CounterArray  // name of counters
);

// internal procedure to get all data from all counters and format for CMK
std::string AccumulateCounters(
    const std::wstring& prefix_name,
    const std::vector<std::wstring_view>& counter_array);

}  // namespace provider

};  // namespace cma

#endif  // perf_counters_cl_h__
