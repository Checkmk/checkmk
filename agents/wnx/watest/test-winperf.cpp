// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include <string>
#include <string_view>

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

namespace wtools {
extern std::vector<int> TsValues;
}

namespace cma::cfg::details {
extern uint64_t g_registered_performance_freq;
}

namespace {
bool ValidIndexOfTs(int index) {
    for (auto a : wtools::TsValues)
        if (a == index) return true;

    return false;
}
}  // namespace

namespace cma::provider {  // to become friendly for wtools classes

auto GetIndexOfTS() {
    uint32_t key_index = 0;
    auto r = details::LoadWinPerfData(L"Terminal Services", key_index);
    return key_index;
}

TEST(WinPerf, GetPerformanceFrequency) {
    auto pf = cfg::GetPerformanceFrequency();
    EXPECT_EQ(cfg::details::g_registered_performance_freq, pf);
}

TEST(WinPerf, ValidateFabricConfig) {
    namespace groups = cma::cfg::groups;
    namespace vars = cma::cfg::vars;
    auto temp_fs(tst::TempCfgFs::CreateNoIo());
    ASSERT_TRUE(temp_fs->loadContent(tst::GetFabricYmlContent()));

    auto cmd_line = cfg::groups::winperf.buildCmdLine();
    auto cfg = cma::cfg::GetLoadedConfig();

    auto winperf_node = cfg[groups::kWinPerf];
    ASSERT_TRUE(winperf_node.IsDefined());
    ASSERT_TRUE(winperf_node.IsMap());

    auto wp_group = cfg[groups::kWinPerf];
    auto cfg_timeout = wp_group[vars::kWinPerfTimeout].as<int>(1234567);
    ASSERT_NE(cfg_timeout, 1234567);
    EXPECT_EQ(groups::winperf.timeout(), cfg_timeout);

    EXPECT_TRUE(wp_group[vars::kWinPerfFork].as<bool>(false));
    EXPECT_TRUE(groups::winperf.isFork());

    EXPECT_FALSE(wp_group[vars::kWinPerfTrace].as<bool>(true));
    EXPECT_FALSE(groups::winperf.isTrace());

    auto cfg_prefix =
        wp_group[vars::kWinPerfPrefixName].as<std::string>("1234567");
    ASSERT_EQ(cfg_prefix, vars::kWinPerfPrefixDefault);
    EXPECT_EQ(groups::winperf.prefix(), cfg_prefix);

    auto enabled = cma::cfg::GetVal(groups::kWinPerf, vars::kEnabled, false);
    EXPECT_TRUE(enabled);
    auto counters =
        cma::cfg::GetPairArray(groups::kWinPerf, vars::kWinPerfCounters);
    ASSERT_EQ(counters.size(), 3);
    const cma::cfg::StringPairArray base_counters = {
        {"238", "processor"},
        {"234", "phydisk"},
        {"510", "if"},
    };

    int found_count = 0;
    for (const auto &counter : counters) {
        std::pair<std::string, std::string> counter_low(counter.first,
                                                        counter.second);
        tools::StringLower(counter_low.first);
        tools::StringLower(counter_low.second);
        if (std::ranges::find(base_counters, counter_low) !=
            base_counters.end()) {
            found_count++;
        }
    }

    EXPECT_EQ(found_count, 3) << "not correct counter list in the yml";
}

TEST(WinPerf, BuildCommandLine) {
    auto temp_fs(tst::TempCfgFs::CreateNoIo());
    ASSERT_TRUE(temp_fs->loadContent("global:\n  enabled: yes\n"));
    auto cmd_line = cfg::groups::winperf.buildCmdLine();
    EXPECT_TRUE(cmd_line.empty()) << cmd_line;

    ASSERT_TRUE(temp_fs->loadContent(tst::GetFabricYmlContent()));
    cmd_line = cfg::groups::winperf.buildCmdLine();
    EXPECT_EQ(cmd_line, L"234:phydisk 510:if 238:processor")
        << "validate fabric yaml";
}

TEST(WinPerf, MakeWinPerfStamp) {
    auto x = details::MakeWinPerfStamp(0);
    ASSERT_TRUE(!x.empty());

    auto table = cma::tools::SplitString(x, " ");
    ASSERT_EQ(table.size(), 3);
    EXPECT_EQ(table[1], "0");

    auto value = cma::tools::ConvertToUint64(table[2], 12345678);
    EXPECT_NE(value, 12345678);
    EXPECT_TRUE(value > 1000);
}

TEST(WinPerf, MakeWinPerfHeader) {
    auto x = details::MakeWinPerfHeader(L"wp", L"zzz");
    EXPECT_EQ(x, "<<<wp_zzz>>>\n");
    x = details::MakeWinPerfHeader(L"www", L"");
    EXPECT_EQ(x, "<<<www_>>>\n");
}
TEST(WinPerf, MakeBodyForTSIntegration) {
    auto ts_index = GetIndexOfTS();
    ASSERT_TRUE(ValidIndexOfTs(ts_index)) << "not supported index " << ts_index;

    uint32_t key_index = 0;
    auto result =
        details::LoadWinPerfData(std::to_wstring(ts_index), key_index);

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

TEST(WinPerf, InvalidCounter) {
    auto name = L"ifxz";
    auto index = L"12345510";
    auto x = BuildWinPerfSection(L"winp", name, index);
    EXPECT_TRUE(x.empty());
}

TEST(WinPerf, IfCounter) {
    using namespace std::string_literals;
    auto x = BuildWinPerfSection(L"winp", L"if", L"510");
    ASSERT_TRUE(!x.empty());

    // check all
    auto table = cma::tools::SplitString(x, "\n");
    ASSERT_TRUE(table.size() > 3);

    // check header
    EXPECT_EQ(table[0], "<<<winp_if>>>"s);
    auto stamp = cma::tools::SplitString(table[1], " ");
    ASSERT_EQ(stamp.size(), 3);

    // check stamp
    auto stamp_time = cma::tools::ConvertToUint64(stamp[0], 12345678);
    EXPECT_NE(stamp_time, 12345678);
    EXPECT_TRUE(stamp_time > 100000);  // we are sure that time is going

    auto stamp_index = cma::tools::ConvertToUint64(stamp[1], 12345678);
    EXPECT_EQ(std::to_string(stamp_index), "510");

    auto stamp_counter = cma::tools::ConvertToUint64(stamp[2], 12345678);
    EXPECT_EQ(stamp_counter, cma::cfg::GetPerformanceFrequency());
}

TEST(WinPerf, TcpConnCounter) {
    auto x = BuildWinPerfSection(L"winperf", L"tcp_conn", L"638");
    ASSERT_TRUE(!x.empty());

    auto table = tools::SplitString(x, "\n");
    ASSERT_TRUE(table.size() > 3);
}

TEST(WinPerf, PhyDiskCounter) {
    auto x = BuildWinPerfSection(L"winperf", L"phydisk", L"234");
    ASSERT_TRUE(!x.empty());

    auto table = tools::SplitString(x, "\n");
    ASSERT_TRUE(table.size() > 3);
}

TEST(WinPerf, TsCounter) {
    using namespace std::string_view_literals;
    auto index_iofts = GetIndexOfTS();
    ASSERT_TRUE(ValidIndexOfTs(index_iofts))  // windows 10 latest
        << "not supported index " << index_iofts << std::endl;
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
        constexpr const wchar_t *name = L"ts_sessions";
        constexpr const wchar_t *index = L"Terminal Services";
        auto x = BuildWinPerfSection(L"winperf", name, index);
        ASSERT_TRUE(!x.empty());

        // check all
        auto table = cma::tools::SplitString(x, "\n");
        ASSERT_TRUE(table.size() > 3);
        auto words = cma::tools::SplitString(table[2], " ");
        EXPECT_EQ(words.size(), 3);
    }
}

}  // namespace cma::provider
