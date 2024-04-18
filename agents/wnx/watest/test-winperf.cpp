// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include <ranges>
#include <string>
#include <string_view>

#include "common/cfg_info.h"
#include "common/wtools.h"
#include "providers/p_perf_counters.h"
#include "tools/_misc.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"
#include "wnx/cfg_details.h"
#include "wnx/service_processor.h"

using namespace std::string_literals;
namespace rs = std::ranges;

namespace {
bool ValidIndexOfTs(int index) {
    return rs::any_of(tst::g_terminal_services_indexes,
                      [index](const auto &e) { return e == index; });
}
}  // namespace

namespace cma::provider {  // to become friendly for wtools classes

auto GetIndexOfTs() {
    uint32_t key_index = 0;
    auto r = details::LoadWinPerfData(L"Terminal Services", key_index);
    return key_index;
}

TEST(WinPerf, ValidateFabricConfig) {
    namespace groups = cfg::groups;
    namespace vars = cfg::vars;
    auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadContent(tst::GetFabricYmlContent()));

    auto cmd_line = cfg::groups::g_winperf.buildCmdLine();
    auto cfg = cfg::GetLoadedConfig();

    auto winperf_node = cfg[groups::kWinPerf];
    ASSERT_TRUE(winperf_node.IsDefined());
    ASSERT_TRUE(winperf_node.IsMap());

    auto wp_group = cfg[groups::kWinPerf];
    auto cfg_timeout = wp_group[vars::kWinPerfTimeout].as<int>(1234567);
    ASSERT_NE(cfg_timeout, 1234567);
    EXPECT_EQ(groups::g_winperf.timeout(), cfg_timeout);

    EXPECT_FALSE(wp_group[vars::kWinPerfFork].as<bool>(true));
    EXPECT_FALSE(groups::g_winperf.isFork());

    EXPECT_FALSE(wp_group[vars::kWinPerfTrace].as<bool>(true));
    EXPECT_FALSE(groups::g_winperf.isTrace());

    auto cfg_prefix =
        wp_group[vars::kWinPerfPrefixName].as<std::string>("1234567");
    ASSERT_EQ(cfg_prefix, vars::kWinPerfPrefixDefault);
    EXPECT_EQ(groups::g_winperf.prefix(), cfg_prefix);

    auto enabled = cfg::GetVal(groups::kWinPerf, vars::kEnabled, false);
    EXPECT_TRUE(enabled);
    auto counters = cfg::GetPairArray(groups::kWinPerf, vars::kWinPerfCounters);
    ASSERT_EQ(counters.size(), 3);
    const cfg::StringPairArray base_counters = {
        {"238", "processor"},
        {"234", "phydisk"},
        {"510", "if"},
    };

    int found_count = 0;
    for (const auto &[section, value] : counters) {
        std::pair counter_low(section, value);
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
    const auto temp_fs{tst::TempCfgFs::CreateNoIo()};
    ASSERT_TRUE(temp_fs->loadContent("global:\n  enabled: yes\n"));
    auto cmd_line = cfg::groups::g_winperf.buildCmdLine();
    EXPECT_TRUE(cmd_line.empty()) << cmd_line;

    ASSERT_TRUE(temp_fs->loadContent(tst::GetFabricYmlContent()));
    cmd_line = cfg::groups::g_winperf.buildCmdLine();
    EXPECT_EQ(cmd_line, L"234:phydisk 510:if 238:processor")
        << "validate fabric yaml";
}

TEST(WinPerf, MakeWinPerfStamp) {
    const auto x = details::MakeWinPerfStamp(0);
    const auto table = tools::SplitString(x, " ");
    ASSERT_EQ(table.size(), 3);
    EXPECT_EQ(table[1], "0");

    const auto value = tools::ConvertToUint64(table[2], 12345678);
    EXPECT_NE(value, 12345678);
    EXPECT_TRUE(value > 1000);
}

TEST(WinPerf, MakeWinPerfHeader) {
    EXPECT_EQ(details::MakeWinPerfHeader(L"wp", L"zzz"), "<<<wp_zzz>>>\n");
    EXPECT_EQ(details::MakeWinPerfHeader(L"www", L""), "<<<www_>>>\n");
}

std::pair<wtools::perf::DataSequence, uint32_t> GetKeyIndex() {
    const auto ts_index = GetIndexOfTs();
    EXPECT_TRUE(ValidIndexOfTs(ts_index)) << "not supported index " << ts_index;

    uint32_t key_index = 0;
    auto result =
        details::LoadWinPerfData(std::to_wstring(ts_index), key_index);
    return {std::move(result), key_index};
}
TEST(WinPerf, MakeBodyForTSComponent) {
    auto [result, key_index] = GetKeyIndex();

    auto object = wtools::perf::FindPerfObject(result, key_index);

    EXPECT_NO_THROW(details::MakeWinPerfNakedList(nullptr, key_index));
    EXPECT_NO_THROW(details::MakeWinPerfNakedList(nullptr, -1));
    EXPECT_NO_THROW(details::MakeWinPerfNakedList(object, 1));

    auto str = details::MakeWinPerfNakedList(object, key_index);
    auto table = tools::SplitString(str, "\n");
    ASSERT_TRUE(!table.empty());
    for (const auto &row : table) {
        auto words = tools::SplitString(row, " ");
        EXPECT_EQ(words.size(), 3);
        EXPECT_NE(tools::ConvertToUint64(words[0], 12345), 12345)
            << "words[0] must be number";
        EXPECT_NE(tools::ConvertToUint64(words[1], 12345), 12345)
            << "words[1] must be number";
        EXPECT_EQ(tools::ConvertToUint64(words[2], 12345), 12345)
            << "words[2] must be NOT number";
    }
}

TEST(WinPerf, InvalidCounter) {
    constexpr auto name = L"ifxz";
    constexpr auto index = L"12345510";
    EXPECT_TRUE(BuildWinPerfSection(L"winp", name, index).empty());
}

bool IsMacLike(const std::string &s) {
    return tools::SplitString(s, ":").size() == 8;
}

TEST(WinPerf, IfCounter) {
    const auto x = BuildWinPerfSection(L"winp", L"if", L"510");
    const auto table = tools::SplitString(x, "\n");
    ASSERT_TRUE(table.size() > 3);

    // check header
    EXPECT_EQ(table[0], "<<<winp_if>>>"s);
    const auto stamp = tools::SplitString(table[1], " ");
    ASSERT_EQ(stamp.size(), 3);
    const auto names = tools::SplitString(table[2], " ");

    // check stamp
    const auto stamp_time = tools::ConvertToUint64(stamp[0], 12345678);
    EXPECT_NE(stamp_time, 12345678);
    EXPECT_TRUE(stamp_time > 100000);  // we are sure that time is going

    EXPECT_EQ(std::to_string(tools::ConvertToUint64(stamp[1], 12345678)),
              "510");
    EXPECT_EQ(tools::ConvertToUint64(stamp[2], 12345678),
              cfg::GetPerformanceFrequency());
    // check at least one negative value is in
    EXPECT_TRUE(rs::any_of(table, [](auto &l) { return l[0] == '-'; }));

    // check pseudo counter is in last line
    EXPECT_TRUE(table[table.size() - 2].starts_with(
        wtools::ToUtf8(winperf::if_state_pseudo_counter)));

    // check pseudo counter is in last line
    EXPECT_TRUE(table[table.size() - 2].ends_with(
        wtools::ToUtf8(winperf::if_state_pseudo_counter_type)));
    // check pseudo counter is in last line
    EXPECT_TRUE(table[table.size() - 1].starts_with(
        wtools::ToUtf8(winperf::if_mac_pseudo_counter)));
    auto pre_last_row = tools::SplitString(table[table.size() - 2], " ");
    EXPECT_EQ(pre_last_row.size(), names.size());

    // check pseudo counter is in last line
    EXPECT_TRUE(table[table.size() - 1].ends_with(
        wtools::ToUtf8(winperf::if_mac_pseudo_counter_type)));
    auto last_row = tools::SplitString(table[table.size() - 1], " ");
    EXPECT_EQ(last_row.size(), names.size());
    EXPECT_TRUE(rs::all_of(std::next(last_row.begin()),
                           std::prev(last_row.end()),
                           [](const std ::string &e) { return IsMacLike(e); }))
        << "Not all MACs found in:" << table[table.size() - 1];
}

TEST(WinPerf, TcpConnCounter) {
    const auto x = BuildWinPerfSection(L"winperf", L"tcp_conn", L"638");
    ASSERT_GT(tools::SplitString(x, "\n").size(), 3U);
}

TEST(WinPerf, PhyDiskCounter) {
    const auto x = BuildWinPerfSection(L"winperf", L"phydisk", L"234");
    ASSERT_GT(tools::SplitString(x, "\n").size(), 3U);
}

TEST(WinPerf, TsCounterByIndex) {
    const auto index_iofts = GetIndexOfTs();
    ASSERT_TRUE(ValidIndexOfTs(index_iofts))  // windows 10 latest
        << "not supported index " << index_iofts << std::endl;

    const auto x = BuildWinPerfSection(L"winperf", std::to_wstring(index_iofts),
                                       std::to_wstring(index_iofts));
    ASSERT_TRUE(tools::SplitString(x, "\n").size() > 3U);
}

TEST(WinPerf, TsCounterByName) {
    const auto index_iofts = GetIndexOfTs();

    uint32_t key_index = 0;
    const auto r = details::LoadWinPerfData(L"Terminal Services", key_index);
    EXPECT_EQ(key_index, index_iofts);
    EXPECT_TRUE(r.len_ != 0);
    EXPECT_TRUE(r.data_ != nullptr);
    EXPECT_NE(wtools::perf::FindPerfObject(r, key_index), nullptr);
}

TEST(WinPerf, TsCounterFull) {
    constexpr auto name = L"ts_sessions";
    constexpr auto index = L"Terminal Services";
    const auto x = BuildWinPerfSection(L"winperf", name, index);
    ASSERT_TRUE(!x.empty());

    const auto table = tools::SplitString(x, "\n");
    ASSERT_TRUE(table.size() > 3);
    EXPECT_EQ(tools::SplitString(table[2], " ").size(), 3);
}

}  // namespace cma::provider
