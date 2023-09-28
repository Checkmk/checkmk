// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include "wnx/cfg.h"
#include "common/wtools.h"
#include "providers/ps.h"
#include "wnx/service_processor.h"
#include "watest/test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

using namespace std::string_literals;
using namespace std::string_view_literals;

namespace cma::provider {
namespace {
long long convert(const std::string &value) {
    try {
        return std::stoll(value);
    } catch (const std::invalid_argument &) {
        return -1;
    }
}

const std::vector<std::string_view> g_special_processes{
    {"System Idle Process"sv},
    {"Memory"sv},
    {"Registry"sv},
    {"Memory Compression"sv},
    {"vmmem"sv},
    {"Secure System"sv},
    {"init"sv},
    {"fish"sv},
    {"wininit.exe"sv},
    {"LsaIso.exe"sv},
    {"bash"sv},
    {"git.exe"sv},
};

}  // namespace

TEST(PsTest, Component) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    for (auto use_full_path : {false, true}) {
        SCOPED_TRACE(
            fmt::format("'{}'", use_full_path ? "Full path" : "Short path"));
        auto out = ProducePsWmi(use_full_path);
        EXPECT_EQ(use_full_path,
                  out.find("svchost.exe\t-k") != std::string::npos);
        auto all = tools::SplitString(out, "\n");
        for (const auto &in : all) {
            auto by_tab = tools::SplitString(in, "\t");
            EXPECT_TRUE(all.size() > 10);
            SCOPED_TRACE(fmt::format("'{}'", in));

            EXPECT_GE(by_tab.size(), 2U);
            ASSERT_EQ(by_tab[0].back(), ')');
            ASSERT_EQ(by_tab[0][0], '(');
            EXPECT_FALSE(by_tab[1].empty());
            auto process_name = by_tab[1];
            auto special =
                std::ranges::find(g_special_processes, process_name) !=
                g_special_processes.end();

            by_tab[0].erase(0, 1);
            by_tab[0].pop_back();
            auto by_comma = tools::SplitString(by_tab[0], ",");
            ASSERT_EQ(by_comma.size(), 11);

            EXPECT_TRUE(!by_comma[0].empty());

            EXPECT_TRUE(convert(by_comma[1]) >= 0);
            if (!special) {
                EXPECT_TRUE(convert(by_comma[2]) > 0);
            }
            EXPECT_TRUE(convert(by_comma[3]) == 0);
            if (!special) {
                EXPECT_TRUE(convert(by_comma[4]) > 0) << by_tab[1];
            }
            EXPECT_TRUE(convert(by_comma[5]) >= 0);
            EXPECT_TRUE(convert(by_comma[6]) >= 0);
            EXPECT_TRUE(convert(by_comma[7]) >= 0);
            if (!special) {
                EXPECT_TRUE(convert(by_comma[8]) > 0) << by_tab[1];
                EXPECT_TRUE(convert(by_comma[9]) > 0)
                    << "'" << process_name << "'";
            }
            EXPECT_TRUE(convert(by_comma[10]) >= 0) << by_comma[10];
        }
    }
}

TEST(PsTest, ConvertWmiTimeInvalid) {
    std::string in = "2019052313140";

    auto check_time = ConvertWmiTimeToHumanTime(in);
    EXPECT_EQ(check_time, 0);
    EXPECT_EQ(ConvertWmiTimeToHumanTime(""), 0);
}

namespace {

auto ToTm(const std::string &in) {
    auto check_time = ConvertWmiTimeToHumanTime(in);
    return *std::localtime(&check_time);  // NOLINT
}

bool IsAccountExist(const std::string &account) {
    SID_NAME_USE snu;
    SID sid = {};
    auto sz = static_cast<DWORD>(sizeof sid);
    DWORD rd_size = {};
    char *rd{nullptr};
    auto success = ::LookupAccountNameA(nullptr, account.c_str(), &sid, &sz, rd,
                                        &rd_size, &snu);
    return success || ::GetLastError() != ERROR_INSUFFICIENT_BUFFER;
}

}  // namespace

TEST(PsTest, ConvertWmiTimeValid) {
    auto check_tm = ToTm("20190523131406.074948+120"s);
    EXPECT_EQ(check_tm.tm_hour, 13);
    EXPECT_EQ(check_tm.tm_sec, 06);
    EXPECT_EQ(check_tm.tm_min, 14);
    EXPECT_EQ(check_tm.tm_year, 119);
    EXPECT_EQ(check_tm.tm_mon, 4);
    EXPECT_EQ(check_tm.tm_mday, 23);

    check_tm = ToTm("20190323090106.074948+120"s);
    EXPECT_EQ(check_tm.tm_hour, 9);
    EXPECT_EQ(check_tm.tm_sec, 6);
    EXPECT_EQ(check_tm.tm_min, 1);
    EXPECT_EQ(check_tm.tm_year, 119);
    EXPECT_EQ(check_tm.tm_mon, 2);
    EXPECT_EQ(check_tm.tm_mday, 23);

    check_tm = ToTm("20000209090909.074948+120"s);
    EXPECT_EQ(check_tm.tm_hour, 9);
    EXPECT_EQ(check_tm.tm_sec, 9);
    EXPECT_EQ(check_tm.tm_min, 9);
    EXPECT_EQ(check_tm.tm_year, 100);
    EXPECT_EQ(check_tm.tm_mon, 1);
    EXPECT_EQ(check_tm.tm_mday, 9);
}

namespace {
constexpr ULONGLONG virtual_size = 1ULL * 1024 * 1024 * 1024 * 1024;
constexpr ULONGLONG working_set_size = 2ULL * 1024 * 1024 * 1024 * 1024;
constexpr long long pagefile_usage = 3LL * 1024 * 1024 * 1024 * 1024;
constexpr ULONGLONG uptime = 4ULL * 1024ULL * 1024 * 1024 * 1024;
constexpr long long usermode_time = 5LL * 1024 * 1024 * 1024 * 1024;
constexpr long long kernelmode_time = 6LL * 1024 * 1024 * 1024 * 1024;
constexpr long long process_id = 7LL * 1024 * 1024 * 1024 * 1024;
constexpr long long process_handle_count = 8LL * 1024 * 1024 * 1024 * 1024;
constexpr long long thread_count = 9LL * 1024 * 1024 * 1024 * 1024;

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
                              long long pagefile_usage, uint64_t uptime,
                              uint64_t usermode_time, uint64_t kernelmode_time,
                              long long process_id,
                              long long process_handle_count,
                              long long thread_count, const std::string &user,
                              const std::string &exe_file);

TEST(PsTest, OutputProcessLine) {
    auto process_string =
        OutputProcessLine(virtual_size, working_set_size, pagefile_usage,
                          uptime, usermode_time, kernelmode_time, process_id,
                          process_handle_count, thread_count, user, exe_file);
    auto by_tab = tools::SplitString(process_string, "\t");
    ASSERT_EQ(by_tab.size(), 2);
    ASSERT_EQ(by_tab[0].back(), ')');
    ASSERT_EQ(by_tab[0][0], '(');
    EXPECT_EQ(by_tab[1], exe_file + "\n");

    by_tab[0].erase(0, 1);
    by_tab[0].pop_back();
    auto by_comma = tools::SplitString(by_tab[0], ",");
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
    auto table = tools::SplitString(processes, L"\n");
    EXPECT_TRUE(!processes.empty());
    EXPECT_GT(table.size(), 10UL);
}

TEST(PsTest, GetProcessOwner) {
    auto name = GetProcessOwner(GetCurrentProcessId());
    ASSERT_TRUE(IsAccountExist(name));
}

}  // namespace cma::provider
