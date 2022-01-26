//
// test-runperf.cpp
// and ends there.
//
#include "pch.h"

#include <time.h>

#include <chrono>
#include <filesystem>
#include <future>
#include <string_view>

#include "carrier.h"
#include "cfg.h"
#include "cfg_details.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "common/cmdline_info.h"
#include "common/wtools.h"
#include "logger.h"
#include "providers/p_perf_counters.h"
#include "providers/perf_counters_cl.h"
#include "read_file.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_raii.h"

constexpr const wchar_t *kUniqueTestId = L"0345246";
struct TestStorage {
    std::vector<uint8_t> buffer_;
    bool delivered_;
    uint64_t answer_id_;
    std::string peer_name_;
};

static TestStorage g_mailslot_storage;

// testing callback
bool MailboxCallbackPerfTest(const cma::MailSlot *Slot, const void *Data,
                             int Len, void *Context) {
    using namespace std::chrono;
    auto storage = (TestStorage *)Context;
    if (!storage) {
        XLOG::l.bp("error in param");
        return false;
    }

    // your code is here
    XLOG::l.i("Received [{}] bytes", Len);

    auto fname = cma::cfg::GetCurrentLogFileName();

    auto dt = static_cast<const cma::carrier::CarrierDataHeader *>(Data);
    switch (dt->type()) {
        case cma::carrier::DataType::kLog:
            // IMPORTANT ENTRY POINT
            // Receive data for Logging to file
            XLOG::l(XLOG::kNoPrefix)(  // command to out to file
                "{} : {}", dt->providerId(), (const char *)dt->data());
            break;

        case cma::carrier::DataType::kSegment:
            // IMPORTANT ENTRY POINT
            // Receive data for Section
            {
                nanoseconds duration_since_epoch(dt->answerId());
                time_point<steady_clock> tp(duration_since_epoch);
                auto data_source = static_cast<const uint8_t *>(dt->data());
                auto data_end = data_source + dt->length();
                std::vector<uint8_t> vectorized_data(data_source, data_end);
                g_mailslot_storage.buffer_ = vectorized_data;
                g_mailslot_storage.answer_id_ = dt->answerId();
                g_mailslot_storage.peer_name_ = dt->providerId();
                g_mailslot_storage.delivered_ = true;
                break;
            }

        case cma::carrier::DataType::kYaml:
            break;
    }

    return true;
}

namespace cma::provider {

TEST(SectionPerf, Runner) {
    //
    cma::MailSlot mailbox("WinAgentPerfTest", 0);

    using namespace cma::carrier;
    using namespace cma::exe;
    using namespace std::chrono_literals;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    mailbox.ConstructThread(MailboxCallbackPerfTest, 20, &g_mailslot_storage,
                            wtools::SecurityLevel::standard);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());

    // prepare parameters
    std::wstring port_param(internal_port.begin(), internal_port.end());

    std::vector<std::wstring_view> counters = {
        L"234:phydisk",                     // 0
        L"238:processor",                   // 1
        L"Terminal*Services:ts_sessions"};  // 2

    const std::wstring prefix = L"winperf";

    auto accu = AccumulateCounters(prefix, counters);

    {
        ASSERT_TRUE(accu.size() > 0);

        auto table = cma::tools::SplitString(accu, "\n");

        int headers_count = 0;
        for (const auto &line : table)
            if (line.find("<<<") != std::string::npos) headers_count++;

        EXPECT_EQ(headers_count, 3);
        EXPECT_NE(accu.find("winperf_phydisk"), std::string::npos);
        EXPECT_NE(accu.find("winperf_processor"), std::string::npos);
        EXPECT_NE(accu.find("winperf_ts_sessions"), std::string::npos);
    }

    auto ret = RunPerf(prefix, port_param, L"12345", 20, counters);
    ASSERT_EQ(ret, 0);
    ASSERT_TRUE(tst::WaitForSuccessIndicate(
        4s, []() { return g_mailslot_storage.delivered_; }));

    auto data = g_mailslot_storage.buffer_.data();
    auto data_end = data + g_mailslot_storage.buffer_.size();
    accu = std::string(data, data_end);
    {
        ASSERT_TRUE(accu.size() > 0);

        auto table = cma::tools::SplitString(accu, "\n");

        int headers_count = 0;
        for (const auto &line : table)
            if (line.find("<<<") != std::string::npos) headers_count++;

        EXPECT_EQ(headers_count, 3);
        EXPECT_NE(accu.find("winperf_phydisk"), std::string::npos);
        EXPECT_NE(accu.find("winperf_processor"), std::string::npos);
        EXPECT_NE(accu.find("winperf_ts_sessions"), std::string::npos);
    }
    //
}

}  // namespace cma::provider
