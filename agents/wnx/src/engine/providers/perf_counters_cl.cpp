// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "stdafx.h"

#include "providers/perf_counters_cl.h"

#include <string>
#include <string_view>

#include "cfg.h"
#include "common/cmdline_info.h"
#include "common/wtools.h"
#include "logger.h"
#include "providers/p_perf_counters.h"

namespace cma::provider {

namespace {
void RemoveTrailingCR(std::string &accu) {
    if (!accu.empty() && accu.back() == '\n') {
        accu.pop_back();
    }
}
}  // namespace

std::string AccumulateCounters(
    std::wstring_view prefix_name,
    const std::vector<std::wstring_view> &counter_array) {
    std::string accu;
    for (const auto &cur_counter : counter_array) {
        auto [key, name] =
            tools::ParseKeyValue(cur_counter, exe::cmdline::kSplitter);

        // ip is not a real counter
        if (key == L"ip") {
            XLOG::d.i("From ip {}", wtools::ToUtf8(name));
            continue;
        }

        std::ranges::replace(key, L'*', L' ');

        if (!name.empty() && !key.empty())
            accu += provider::BuildWinPerfSection(prefix_name, name, key);
    }

    RemoveTrailingCR(accu);

    XLOG::d.i("Gathered {} bytes of winperf data", accu.size());

    return accu;
}

// workhorse of execution
// accumulates all data in counters
// sends accumulated data to internal port
// return 0 on success
int RunPerf(
    const std::wstring &peer_name,  // name assigned by starting program
    const std::wstring &port,       // format as in carrier.h mail:*
    const std::wstring &answer_id,  // answer id, should be set
    int /*timeout*/,                // how long wait for execution
    const std::vector<std::wstring_view> counter_array  // name of counters
) {
    auto accu = AccumulateCounters(peer_name, counter_array);

    auto result = carrier::CoreCarrier::FireSend(peer_name, port, answer_id,
                                                 accu.c_str(), accu.size());
    XLOG::d.i("Send at port '{}' '{}' by '{}' [{}]", wtools::ToUtf8(port),
              result ? "success" : "failed", wtools::ToUtf8(peer_name),
              accu.size());

    return result ? 0 : -1;
}

};  // namespace cma::provider
