// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include "cfg.h"
#include "common/wtools.h"
#include "providers/ps.h"
#include "service_processor.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::provider {
namespace {
long long convert(const std::string &value) {
    try {
        return std::stoull(value);
    } catch (...) {
        return -1;
    }
}

using namespace std::string_view_literals;

const std::vector<std::string_view> special_processes{
    {"System Idle Process"sv}, {"Memory"sv}, {"Registry"sv},
    {"Memory Compression"sv},  {"vmmem"sv},  {"Secure System"sv}};

}  // namespace

TEST(PsTest, Integration) {
    cma::OnStart(cma::AppType::test);
    for (auto use_full_path : {false, true}) {
        SCOPED_TRACE(
            fmt::format("'{}'", use_full_path ? "Full path" : "Short path"));
        auto out = ProducePsWmi(use_full_path);
        EXPECT_EQ(use_full_path,
                  out.find("svchost.exe\t-k") != std::string::npos);
        auto all = cma::tools::SplitString(out, "\n");
        EXPECT_TRUE(all.size() > 10);
        for (auto &in : all) {
            auto by_tab = cma::tools::SplitString(in, "\t");
            SCOPED_TRACE(fmt::format("'{}'", in));

            EXPECT_GE(by_tab.size(), 2U);
            ASSERT_EQ(by_tab[0].back(), ')');
            ASSERT_EQ(by_tab[0][0], '(');
            EXPECT_TRUE(by_tab[1].size() > 0);
            auto process_name = by_tab[1];
            auto special =
                std::find(special_processes.begin(), special_processes.end(),
                          process_name) != special_processes.end();

            by_tab[0].erase(0, 1);
            by_tab[0].pop_back();
            auto by_comma = cma::tools::SplitString(by_tab[0], ",");
            ASSERT_EQ(by_comma.size(), 11);

            EXPECT_TRUE(!by_comma[0].empty());

            auto result = convert(by_comma[1]);
            EXPECT_TRUE(convert(by_comma[1]) >= 0);
            if (!special) EXPECT_TRUE(convert(by_comma[2]) > 0);
            EXPECT_TRUE(convert(by_comma[3]) == 0);
            if (!special) EXPECT_TRUE(convert(by_comma[4]) > 0) << by_tab[1];
            EXPECT_TRUE(convert(by_comma[5]) >= 0);
            EXPECT_TRUE(convert(by_comma[6]) >= 0);
            EXPECT_TRUE(convert(by_comma[7]) >= 0);
            if (!special) EXPECT_TRUE(convert(by_comma[8]) > 0) << by_tab[1];
            if (!special)
                EXPECT_TRUE(convert(by_comma[9]) > 0)
                    << "'" << process_name << "'";
            EXPECT_TRUE(convert(by_comma[10]) >= 0) << by_comma[10];
        }
    }
}

TEST(PsTest, ConvertWmiTime) {
    {
        std::string in = "2019052313140";

        auto check_time = ConvertWmiTimeToHumanTime(in);
        EXPECT_EQ(check_time, 0);
        EXPECT_EQ(ConvertWmiTimeToHumanTime(""), 0);
    }

    {
        std::string in = "20190523131406.074948+120";

        auto check_time = ConvertWmiTimeToHumanTime(in);
        auto check_tm = *std::localtime(&check_time);
        EXPECT_EQ(check_tm.tm_hour, 13);
        EXPECT_EQ(check_tm.tm_sec, 06);
        EXPECT_EQ(check_tm.tm_min, 14);
        EXPECT_EQ(check_tm.tm_year, 119);
        EXPECT_EQ(check_tm.tm_mon, 4);
        EXPECT_EQ(check_tm.tm_mday, 23);
    }

    {
        std::string in = "20190323090106.074948+120";

        auto check_time = ConvertWmiTimeToHumanTime(in);
        auto check_tm = *std::localtime(&check_time);
        EXPECT_EQ(check_tm.tm_hour, 9);
        EXPECT_EQ(check_tm.tm_sec, 6);
        EXPECT_EQ(check_tm.tm_min, 1);
        EXPECT_EQ(check_tm.tm_year, 119);
        EXPECT_EQ(check_tm.tm_mon, 2);
        EXPECT_EQ(check_tm.tm_mday, 23);
    }

    {
        std::string in = "20000209090909.074948+120";

        auto check_time = ConvertWmiTimeToHumanTime(in);
        auto check_tm = *std::localtime(&check_time);
        EXPECT_EQ(check_tm.tm_hour, 9);
        EXPECT_EQ(check_tm.tm_sec, 9);
        EXPECT_EQ(check_tm.tm_min, 9);
        EXPECT_EQ(check_tm.tm_year, 100);
        EXPECT_EQ(check_tm.tm_mon, 1);
        EXPECT_EQ(check_tm.tm_mday, 9);
    }
}

namespace {
constexpr ULONGLONG virtual_size = 1ull * 1024 * 1024 * 1024 * 1024;
constexpr ULONGLONG working_set_size = 2ull * 1024 * 1024 * 1024 * 1024;
constexpr long long pagefile_usage = 3ll * 1024 * 1024 * 1024 * 1024;
constexpr ULONGLONG uptime = 4ull * 1024ull * 1024 * 1024 * 1024;
constexpr long long usermode_time = 5ll * 1024 * 1024 * 1024 * 1024;
constexpr long long kernelmode_time = 6ll * 1024 * 1024 * 1024 * 1024;
constexpr long long process_id = 7ll * 1024 * 1024 * 1024 * 1024;
constexpr long long process_handle_count = 8ll * 1024 * 1024 * 1024 * 1024;
constexpr long long thread_count = 9ll * 1024 * 1024 * 1024 * 1024;

const std::string user = "user";
const std::string exe_file = "exe_file";

}  // namespace

// This internal function will be tested intentionally.
// Motivation. We have the problem:
// - cant put this function into public API as implementation
// - have to test the function because it is complicated part the of business
// logic.
// Decision: "Test internal API explicit"
std::string OutputProcessLine(ULONGLONG virtual_size,
                              ULONGLONG working_set_size,
                              long long pagefile_usage, ULONGLONG uptime,
                              long long usermode_time,
                              long long kernelmode_time, long long process_id,
                              long long process_handle_count,
                              long long thread_count, const std::string &user,
                              const std::string &exe_file);

TEST(PsTest, OutputProcessLine) {
    auto process_string =
        OutputProcessLine(virtual_size, working_set_size, pagefile_usage,
                          uptime, usermode_time, kernelmode_time, process_id,
                          process_handle_count, thread_count, user, exe_file);
    auto by_tab = cma::tools::SplitString(process_string, "\t");
    ASSERT_EQ(by_tab.size(), 2);
    ASSERT_EQ(by_tab[0].back(), ')');
    ASSERT_EQ(by_tab[0][0], '(');
    EXPECT_EQ(by_tab[1], exe_file + "\n");

    by_tab[0].erase(0, 1);
    by_tab[0].pop_back();
    auto by_comma = cma::tools::SplitString(by_tab[0], ",");
    ASSERT_EQ(by_comma.size(), 11);

    EXPECT_EQ(by_comma[0], user);

    EXPECT_EQ(convert(by_comma[1]), virtual_size / 1024);
    EXPECT_EQ(convert(by_comma[2]), working_set_size / 1024);
    EXPECT_EQ(convert(by_comma[3]), 0);
    EXPECT_EQ(convert(by_comma[4]), process_id);
    EXPECT_EQ(convert(by_comma[5]), pagefile_usage / 1024);
    EXPECT_EQ(convert(by_comma[6]), usermode_time);
    EXPECT_EQ(convert(by_comma[7]), kernelmode_time);
    EXPECT_EQ(convert(by_comma[8]), process_handle_count);
    EXPECT_EQ(convert(by_comma[9]), thread_count);
    EXPECT_EQ(convert(by_comma[10]), uptime);
}

TEST(PsTest, GetProcessListFromWmi) {
    auto processes = GetProcessListFromWmi(ps::kSepString);
    auto table = cma::tools::SplitString(processes, L"\n");
    EXPECT_TRUE(!processes.empty());
    EXPECT_GT(table.size(), 10UL);
}

}  // namespace cma::provider
