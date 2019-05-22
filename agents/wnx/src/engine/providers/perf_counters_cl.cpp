
// provides basic api to start and stop service
// Command Line entry point

#include "stdafx.h"

#include "providers/perf_counters_cl.h"

#include <string>

#include "cfg.h"
#include "common/cmdline_info.h"
#include "common/wtools.h"
#include "logger.h"
#include "providers/p_perf_counters.h"
#include "tools/_raii.h"

namespace cma {

namespace provider {

std::string AccumulateCounters(
    const std::wstring& prefix_name,
    const std::vector<std::wstring_view>& counter_array) {
    using namespace cma::tools;

    std::string accu;
    for (const auto& cur_counter : counter_array) {
        auto [key, name] = ParseKeyValue(cur_counter, exe::cmdline::kSplitter);
        if (key == L"ip") {
            XLOG::d.i("From ip {}", wtools::ConvertToUTF8(name));
            continue;
        }

        std::replace(key.begin(), key.end(), L'*', L' ');

        if (!name.empty() && !key.empty())
            accu += cma::provider::BuildWinPerfSection(prefix_name, name, key);

        // sends results to carrier
    }
    if (!accu.empty() && accu.back() == '\n') accu.pop_back();

    return accu;
}

// workhorse of execution
// accumulates all data in counters
// sends accumulated data to internal port
// return 0 on success
int RunPerf(const std::wstring& PeerName,  // name assigned by starting program
            const std::wstring& Port,      // format as in carrier.h mail:*
            const std::wstring& Id,        // answer id, should be set
            int Timeout,                   // how long wait for execution
            std::vector<std::wstring_view> CounterArray  // name of counters
) {
    auto accu = AccumulateCounters(PeerName, CounterArray);

    auto result = cma::carrier::CoreCarrier::FireSend(
        PeerName, Id, Port, accu.c_str(), accu.size());
    XLOG::d.i("Send to {} {}", wtools::ConvertToUTF8(Port), accu.size());
    return result ? 0 : -1;
}

}  // namespace provider
};  // namespace cma
