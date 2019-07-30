// test-winperf.cpp

//
#include "pch.h"

#include "carrier.h"
#include "cfg.h"
#include "cfg_details.h"
#include "common/cfg_info.h"
#include "common/wtools.h"
#include "providers/p_perf_counters.h"
#include "read_file.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::cfg::details {
extern uint64_t RegisteredPerformanceFreq;
}

namespace cma::provider {  // to become friendly for wtools classes

auto GetIndexOfTS() {
    uint32_t key_index = 0;
    auto r = details::LoadWinPerfData(L"Terminal Services", key_index);
    return key_index;
}

TEST(WinPerfTest, Pre) {
    auto pf = cma::cfg::GetPerformanceFrequency();
    EXPECT_EQ(cma::cfg::details::RegisteredPerformanceFreq, pf)
        << "Something wrong and value was not initialized";
}

TEST(WinPerfTest, YmlCheck) {
    using namespace cma::cfg;
    using namespace cma::tools;
    tst::YamlLoader w;
    auto cfg = cma::cfg::GetLoadedConfig();

    auto winperf_node = cfg[groups::kWinPerf];
    ASSERT_TRUE(winperf_node.IsDefined());
    ASSERT_TRUE(winperf_node.IsMap());

    auto enabled = GetVal(groups::kWinPerf, vars::kEnabled, false);
    EXPECT_TRUE(enabled);
    auto counters = GetPairArray(groups::kWinPerf, vars::kWinPerfCounters);
    ASSERT_EQ(counters.size(), 3);
    const StringPairArray base_counters = {
        {"238", "processor"},
        {"234", "phydisk"},
        {"510", "if"},
    };

    int found_count = 0;
    for (const auto& counter : counters) {
        std::pair<std::string, std::string> counter_low(counter.first,
                                                        counter.second);
        StringLower(counter_low.first);
        StringLower(counter_low.second);
        auto found = cma::tools::find(base_counters, counter_low);
        if (found) found_count++;
    }

    EXPECT_EQ(found_count, 3) << "not correct counter list in the yml";
}

TEST(WinPerfTest, RootCalls) {
    //  testing first line stamping
    // 1548673688.07 510 2156253
    auto index_iofts = GetIndexOfTS();
    ASSERT_TRUE(index_iofts == 2066 || index_iofts == 8154)
        << "not supported index " << index_iofts << std::endl;
    {
        auto x = details::MakeWinPerfStamp(0);
        ASSERT_TRUE(!x.empty());

        auto table = cma::tools::SplitString(x, " ");
        ASSERT_EQ(table.size(), 3);
        EXPECT_EQ(table[1], "0");

        auto value = cma::tools::ConvertToUint64(table[2], 12345678);
        EXPECT_NE(value, 12345678);
        EXPECT_TRUE(value > 1000);
    }
    {
        auto x = details::MakeWinPerfHeader(L"wp", L"zzz");
        EXPECT_EQ(x, "<<<wp_zzz>>>\n");
    }

    {
        auto x = details::MakeWinPerfHeader(L"www", L"");
        EXPECT_EQ(x, "<<<www_>>>\n");
    }

    {
        uint32_t key_index = 0;
        auto result =
            details::LoadWinPerfData(std::to_wstring(index_iofts), key_index);

        ASSERT_TRUE(result.len_ > 0);
        auto object = wtools::perf::FindPerfObject(result, key_index);

        EXPECT_NO_THROW(details::MakeWinPerfNakedList(nullptr, key_index));
        EXPECT_NO_THROW(details::MakeWinPerfNakedList(nullptr, -1));
        EXPECT_NO_THROW(details::MakeWinPerfNakedList(object, 1));

        auto str = details::MakeWinPerfNakedList(object, key_index);
        auto table = cma::tools::SplitString(str, "\n");
        ASSERT_TRUE(table.size() > 0);
        for (size_t pos = 0; pos < table.size(); ++pos) {
            auto words = cma::tools::SplitString(table[pos], " ");
            EXPECT_EQ(words.size(), 3);
            EXPECT_NE(cma::tools::ConvertToUint64(words[0], 12345), 12345)
                << "words[0] must be number";
            EXPECT_NE(cma::tools::ConvertToUint64(words[1], 12345), 12345)
                << "words[1] must be number";
            EXPECT_EQ(cma::tools::ConvertToUint64(words[2], 12345), 12345)
                << "words[2] must be NOT number";
        }
    }
}

TEST(WinPerfTest, Calls) {
    auto index_iofts = GetIndexOfTS();
    ASSERT_TRUE(index_iofts == 2066 || index_iofts == 8154)
        << "not supported index " << index_iofts << std::endl;
    {
        constexpr const char* name = "if";
        constexpr const char* index = "510";
        auto x = BuildWinPerfSection(L"winp", wtools::ConvertToUTF16("if"),
                                     wtools::ConvertToUTF16("510"));
        ASSERT_TRUE(!x.empty());

        // check all
        auto table = cma::tools::SplitString(x, "\n");
        ASSERT_TRUE(table.size() > 3);

        // check header
        EXPECT_EQ(table[0], std::string("<<<winp_") + name + ">>>");
        auto stamp = cma::tools::SplitString(table[1], " ");
        ASSERT_EQ(stamp.size(), 3);

        // check stamp
        auto stamp_time = cma::tools::ConvertToUint64(stamp[0], 12345678);
        EXPECT_NE(stamp_time, 12345678);
        EXPECT_TRUE(stamp_time > 100000);  // we are sure that time is going

        auto stamp_index = cma::tools::ConvertToUint64(stamp[1], 12345678);
        EXPECT_EQ(std::to_string(stamp_index), index);

        auto stamp_counter = cma::tools::ConvertToUint64(stamp[2], 12345678);
        EXPECT_EQ(stamp_counter, cma::cfg::GetPerformanceFrequency());
    }
    {
        constexpr const wchar_t* name = L"tcp_conn";
        constexpr const wchar_t* index = L"638";
        auto x = BuildWinPerfSection(L"winperf", name, index);
        ASSERT_TRUE(!x.empty());

        // check all
        auto table = cma::tools::SplitString(x, "\n");
        ASSERT_TRUE(table.size() > 3);
    }

    {
        constexpr const wchar_t* name = L"phydisk";
        constexpr const wchar_t* index = L"234";
        auto x = BuildWinPerfSection(L"winperf", wtools::ConvertToUTF16("if"),
                                     wtools::ConvertToUTF16("510"));
        ASSERT_TRUE(!x.empty());

        // check all
        auto table = cma::tools::SplitString(x, "\n");
        ASSERT_TRUE(table.size() > 3);
    }

    {
        auto x = BuildWinPerfSection(L"winperf", std::to_wstring(index_iofts),
                                     std::to_wstring(index_iofts));
        ASSERT_TRUE(!x.empty());

        // check all
        auto table = cma::tools::SplitString(x, "\n");
        ASSERT_TRUE(table.size() > 3);
    }

    {
        uint32_t key_index = 0;
        auto r = details::LoadWinPerfData(L"Terminal Services", key_index);
        EXPECT_EQ(key_index, index_iofts);
        EXPECT_TRUE(r.len_ != 0);
        EXPECT_TRUE(r.data_ != nullptr);
        auto object = wtools::perf::FindPerfObject(r, key_index);
        EXPECT_TRUE(object != nullptr);
    }

    {
        constexpr const wchar_t* name = L"ts_sessions";
        constexpr const wchar_t* index = L"Terminal Services";
        auto x = BuildWinPerfSection(L"winperf", name, index);
        ASSERT_TRUE(!x.empty());

        // check all
        auto table = cma::tools::SplitString(x, "\n");
        ASSERT_TRUE(table.size() > 3);
        auto words = cma::tools::SplitString(table[2], " ");
        EXPECT_EQ(words.size(), 3);
    }
}

TEST(WinPerfTest, Config) {
    using namespace cma::cfg;
    cma::OnStart(cma::AppType::test);
    {
        auto c = groups::winperf.counters();
        EXPECT_TRUE(c.size() >= 3)
            << "In Config we have to have at least three indexes described";
        auto cmd_line = groups::winperf.buildCmdLine();
        ASSERT_TRUE(!cmd_line.empty());

        auto list = cma::tools::SplitString(cmd_line, L" ");
        ASSERT_TRUE(!list.empty());
        ASSERT_EQ(list.size(), c.size());

        int pos = 0;
        for (auto& l : list) {
            auto words = cma::tools::SplitString(l, L":");
            EXPECT_EQ(words.size(), 2);
            std::replace(words[0].begin(), words[0].end(), '*', ' ');
            EXPECT_EQ(wtools::ConvertToUTF8(words[0]), c[pos].id());
            EXPECT_EQ(wtools::ConvertToUTF8(words[1]), c[pos].name());
            ++pos;
        }
    }
    {
        auto cfg = cma::cfg::GetLoadedConfig();
        auto wp_group = cfg[groups::kWinPerf];
        auto cfg_timeout = wp_group[vars::kWinPerfTimeout].as<int>(1234567);
        ASSERT_NE(cfg_timeout, 1234567);
        EXPECT_EQ(groups::winperf.timeout(), cfg_timeout);

        auto cfg_prefix =
            wp_group[vars::kWinPerfPrefixName].as<std::string>("1234567");
        ASSERT_EQ(cfg_prefix, vars::kWinPerfPrefixDefault);
        EXPECT_EQ(groups::winperf.prefix(), cfg_prefix);
    }
}

}  // namespace cma::provider
