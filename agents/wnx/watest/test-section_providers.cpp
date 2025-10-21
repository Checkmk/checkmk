// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include "common/version.h"
#include "common/wtools.h"
#include "providers/check_mk.h"
#include "providers/df.h"
#include "providers/internal.h"
#include "providers/mem.h"
#include "providers/p_perf_counters.h"
#include "providers/plugins.h"
#include "providers/services.h"
#include "tools/_misc.h"
#include "watest/test_tools.h"
#include "wnx/agent_controller.h"
#include "wnx/cfg.h"
#include "wnx/install_api.h"
#include "wnx/service_processor.h"

namespace fs = std::filesystem;

namespace cma::provider {
static const std::string section_name{section::kUseEmbeddedName};

class Empty final : public Synchronous {
public:
    Empty() : Synchronous("empty") {}
    std::string makeBody() override { return "****"; }
};

TEST(SectionProviders, Basic) {
    Empty e;
    EXPECT_EQ(e.errorCount(), 0);
    EXPECT_EQ(e.timeout(), 0);
    EXPECT_EQ(e.getUniqName(), "empty");
    EXPECT_EQ(e.separator(), '\0');
}

TEST(SectionProviders, PluginsProviderConstruction) {
    PluginsProvider plugins;
    EXPECT_EQ(plugins.getUniqName(), section::kPlugins);
}

TEST(SectionProviders, LocalProviderConstruction) {
    LocalProvider local;
    EXPECT_EQ(local.getUniqName(), section::kLocal);
}

TEST(SectionProviders, BasicUptime) {
    srv::SectionProvider<provider::UptimeSync> uptime_provider;
    EXPECT_EQ(uptime_provider.getEngine().getUniqName(), section::kUptimeName);

    auto &e3 = uptime_provider.getEngine();
    auto uptime = e3.generateContent(section_name);
    ASSERT_TRUE(!uptime.empty());
    auto result = tools::SplitString(uptime, "\n");
    EXPECT_EQ(result.size(), 2);
    EXPECT_EQ(result[0], "<<<uptime>>>");
    auto value = result[1].find_first_not_of("0123456789");
    EXPECT_EQ(value, std::string::npos);
}

TEST(SectionProviders, BasicDf) {
    srv::SectionProvider<provider::Df> df_provider;
    EXPECT_EQ(df_provider.getEngine().getUniqName(), section::kDfName);

    auto &e2 = df_provider.getEngine();
    auto df = e2.generateContent(section_name);
    ASSERT_TRUE(!df.empty());
    auto result = tools::SplitString(df, "\n");
    ASSERT_TRUE(result.size() > 1);
    EXPECT_EQ(result[0], "<<<df:sep(9)>>>");
    auto count = result.size();
    for (size_t i = 1; i < count; ++i) {
        auto values = tools::SplitString(result[i], "\t");
        ASSERT_EQ(values.size(), 7);

        auto ret = values[2].find_first_not_of("0123456789");
        EXPECT_EQ(ret, std::string::npos);

        ret = values[3].find_first_not_of("0123456789");
        EXPECT_EQ(ret, std::string::npos);

        ret = values[4].find_first_not_of("0123456789");
        EXPECT_EQ(ret, std::string::npos);

        EXPECT_EQ(values[5].back(), '%');
    }
}

TEST(SectionProviders, SystemTime) {
    auto seconds_since_epoch = tools::SecondsSinceEpoch();
    srv::SectionProvider<SystemTime> system_time_provider;
    auto &engine = system_time_provider.getEngine();

    EXPECT_EQ(engine.getUniqName(), section::kSystemTime);

    auto system_time = engine.generateContent(section_name);
    EXPECT_EQ(system_time.back(), '\n');

    auto result = tools::SplitString(system_time, "\n");
    ASSERT_EQ(result.size(), 2);
    EXPECT_EQ(result[0], "<<<systemtime>>>");
    auto value = std::stoll(result[1]);
    EXPECT_GE(value, seconds_since_epoch);
}

TEST(SectionProviders_Integration, W32TimeStatus) {
    srv::SectionProvider<W32TimeStatus> w32time_status_provider;
    auto &engine = w32time_status_provider.getEngine();

    static constexpr std::array<std::string_view, 16> kFields{
        "Leap Indicator:",
        "Stratum:",
        "Precision:",
        "Root Delay:",
        "Root Dispersion:",
        "ReferenceId:",
        "Last Successful Sync Time:",
        "Source:",
        "Poll Interval:",
        "Phase Offset:",
        "ClockRate:",
        "State Machine:",
        "Time Source Flags:",
        "Server Role:",
        "Last Sync Error:",
        "Time since Last Good Sync Time:"};

    auto const &content = engine.generateContent(section_name);

    EXPECT_EQ(engine.getUniqName(), section::kW32TimeStatus);
    ASSERT_FALSE(content.empty());
    EXPECT_NE(content.find("<<<w32time_status>>>"), std::string::npos);
    for (auto f : kFields) {
        EXPECT_NE(content.find(f), std::string::npos)
            << "Missing field: " << f << "\nFull output:\n"
            << content;
    }
}

TEST(SectionProviders_Integration, W32TimePeers) {
    srv::SectionProvider<W32TimePeers> w32time_peers_provider;
    auto &engine = w32time_peers_provider.getEngine();
    auto const &content = engine.generateContent(section_name);
    static constexpr std::array<std::string_view, 16> kFields{
        "#Peers:",
        "---",
        "Peer:",
        "State:",
        "Time Remaining:",
        "Mode:",
        "Stratum:",
        "PeerPoll Interval:",
        "HostPoll Interval:",
        "Last Successful Sync Time:",
        "LastSyncError:",
        "LastSyncErrorMsgId:",
        "AuthTypeMsgId:",
        "Resolve Attempts:",
        "ValidDataCounter:",
        "Reachability:"};

    EXPECT_EQ(engine.getUniqName(), section::kW32TimePeers);
    ASSERT_FALSE(content.empty());
    EXPECT_NE(content.find("<<<w32time_peers>>>"), std::string::npos);
    for (auto f : kFields) {
        EXPECT_NE(content.find(f), std::string::npos)
            << "Missing field: " << f << "\nFull output:\n"
            << content;
    }
}

class SectionProviderCheckMkFixture : public ::testing::Test {
public:
    static constexpr size_t core_lines_ = 23;
    static constexpr size_t full_lines_ = core_lines_ + 3;
    static constexpr std::string_view names_[core_lines_ - 1] = {
        "Version",          "BuildDate",        "AgentOS",
        "Hostname",         "Architecture",     "OSName",
        "OSVersion",        "OSType",           "Time",
        "WorkingDirectory", "ConfigFile",       "LocalConfigFile",
        "AgentDirectory",   "PluginsDirectory", "StateDirectory",
        "ConfigDirectory",  "TempDirectory",    "LogDirectory",
        "SpoolDirectory",   "LocalDirectory",   "OnlyFrom"};

    static constexpr std::pair<std::string_view, std::string_view>
        only_from_cases_[] = {
            //
            {"~", ""},
            {"127.0.0.1", "127.0.0.1"},
            {"127.0.0.1 192.168.0.1", "127.0.0.1 192.168.0.1"},
            {"[127.0.0.1, 192.168.0.1]", "127.0.0.1 192.168.0.1"},
            {"[127.0.0.1, ::1]", "127.0.0.1 ::1"},
            {"[127.0.0.1/16, ::1/64]", "127.0.0.1/16 ::1/64"}  //
        };

    std::string getContent() { return getEngine().generateContent(); }
    std::vector<std::string> getFullResultAsTable() {
        return tools::SplitString(getContent(), "\n");
    }
    std::vector<std::string> getCoreResultAsTable() {
        auto result = getFullResultAsTable();
        result.erase(result.begin());
        return result;
    }
    CheckMk &getEngine() { return check_mk_provider_.getEngine(); }

    std::filesystem::path createDataDir() {
        if (!temp_fs_) {
            temp_fs_ = tst::TempCfgFs::Create();
        }
        return temp_fs_->data();
    }

    std::string get_val(const std::string &raw) const {
        auto tbl = tools::SplitString(raw, ": ");
        if (tbl.size() == 2) {
            return tbl[1];
        }

        return {};
    }

private:
    srv::SectionProvider<CheckMk> check_mk_provider_;
    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(SectionProviderCheckMkFixture, Name) {
    EXPECT_EQ(getEngine().getUniqName(), section::kCheckMk);
}

TEST_F(SectionProviderCheckMkFixture, ConstFields) {
    createDataDir();
    auto cfg = cfg::GetLoadedConfig();
    cfg[cfg::groups::kGlobal][cfg::vars::kOnlyFrom] = YAML::Load("127.0.0.1");

    auto result = getCoreResultAsTable();

    const auto *expected_name = names_;
    EXPECT_EQ(result[result.size() - 1] + "\n",
              section::MakeHeader(section::kCheckMkCtlStatus));
    result.pop_back();
    for (const auto &r : result) {
        auto values = tools::SplitString(r, ": ");
        EXPECT_EQ(values[0], std::string{*expected_name++});
        EXPECT_EQ(values.size(), 2);
    }
}

TEST_F(SectionProviderCheckMkFixture, AdvancedFields) {
    createDataDir();
    auto result = getCoreResultAsTable();
    EXPECT_EQ(get_val(result[0]), CHECK_MK_VERSION);
    EXPECT_EQ(get_val(result[2]), "windows");
    EXPECT_EQ(get_val(result[3]), cfg::GetHostName());
    EXPECT_EQ(get_val(result[4]), tgt::Is64bit() ? "64bit" : "32bit");
    EXPECT_EQ(result[result.size() - 1] + "\n",
              section::MakeHeader(section::kCheckMkCtlStatus));
    tst::CreateTextFile(fs::path{cfg::GetUserDir()} / ac::kLegacyPullFile,
                        "test");
    result = getCoreResultAsTable();
    EXPECT_EQ(result[result.size() - 1] + "\n",
              section::MakeHeader(section::kCheckMkCtlStatus));
}

TEST_F(SectionProviderCheckMkFixture, OnlyFromField) {
    createDataDir();
    auto cfg = cfg::GetLoadedConfig();

    for (auto p : only_from_cases_) {
        cfg[cfg::groups::kGlobal][cfg::vars::kOnlyFrom] =
            YAML::Load(std::string{p.first});
        auto result = getCoreResultAsTable();
        result.pop_back();
        EXPECT_EQ(get_val(*std::prev(result.end())), std::string{p.second});
    }
}

TEST_F(SectionProviderCheckMkFixture, FailedPythonInstall) {
    tst::misc::CopyFailedPythonLogFileToLog(createDataDir());

    auto result = getFullResultAsTable();
    EXPECT_EQ(result[full_lines_ - 3] + "\n",
              section::MakeHeader(section::kCheckMk));
    EXPECT_TRUE(result[full_lines_ - 2].starts_with("UpdateFailed:"));
    EXPECT_TRUE(result[full_lines_ - 1].starts_with("UpdateRecoverAction:"));
}

TEST_F(SectionProviderCheckMkFixture, FailedInstallApi) {
    tst::misc::CopyFailedPythonLogFileToLog(createDataDir());
    install::api_err::Register("disaster!");

    auto result = getFullResultAsTable();
    EXPECT_EQ(result[full_lines_ - 3] + "\n",
              section::MakeHeader(section::kCheckMk));
    EXPECT_TRUE(result[full_lines_ - 2].starts_with("UpdateFailed:"));
    EXPECT_TRUE(result[full_lines_ - 2].ends_with("disaster!"));
    EXPECT_TRUE(result[full_lines_ - 1].starts_with(
        "UpdateRecoverAction: Contact with system administrator."));
}

class SectionProvidersMemFixture : public ::testing::Test {
public:
    struct Row {
        std::string title;
        std::string value;
        std::string kb;
    };
    constexpr static std::string_view field_names_[8] = {
        "MemTotal",  "MemFree",  "SwapTotal",    "SwapFree",
        "PageTotal", "PageFree", "VirtualTotal", "VirtualFree"};
    void SetUp() override {
        uniq_name_ = getEngine().getUniqName();
        auto mem = getEngine().generateContent(section_name);
        auto rows = tools::SplitString(mem, "\n");
        header_ = rows[0];
        auto count = rows.size();
        for (size_t i = 1; i < count; ++i) {
            auto values = tools::SplitString(rows[i], ":");
            tools::LeftTrim(values[1]);
            auto sub_values = tools::SplitString(values[1], " ");
            rows_.push_back({.title = values[0],
                             .value = sub_values[0],
                             .kb = sub_values[1]});
        }
    }
    std::string uniq_name_;
    std::string header_;
    std::vector<Row> rows_;

private:
    Mem &getEngine() { return mem_provider_.getEngine(); }
    srv::SectionProvider<Mem> mem_provider_;
};

TEST_F(SectionProvidersMemFixture, Mem) {
    EXPECT_EQ(uniq_name_, section::kMemName);
    EXPECT_EQ(header_, "<<<mem>>>");
    ASSERT_EQ(rows_.size(), 8);
    for (size_t i = 0; i < rows_.size(); ++i) {
        const auto &row = rows_[i];
        EXPECT_EQ(row.title, field_names_[i]);
        EXPECT_TRUE(std::stoll(row.value) > 0);
        EXPECT_EQ(row.kb, "kB");
    }
}

class SectionProvidersFixture : public ::testing::Test {
public:
    Services &getEngine() { return services_provider.getEngine(); }

private:
    srv::SectionProvider<Services> services_provider;
};

TEST_F(SectionProvidersFixture, ServicesCtor) {
    EXPECT_EQ(getEngine().getUniqName(), section::kServices);
}
TEST_F(SectionProvidersFixture, ServicesComponent) {
    auto content = getEngine().generateContent(section_name);

    // Validate content is presented and correct
    ASSERT_TRUE(!content.empty());
    auto result = tools::SplitString(content, "\n");
    EXPECT_TRUE(result.size() > 20);

    // Validate Header
    EXPECT_EQ(result[0], "<<<services>>>");

    // Validate Body
    auto count = result.size();
    for (size_t i = 1; i < count; ++i) {
        auto values = tools::SplitString(result[i], " ", 2);
        EXPECT_FALSE(values[0].empty());
        EXPECT_FALSE(values[1].empty());
        EXPECT_FALSE(values[2].empty());
        EXPECT_TRUE(values[1].find("/") != std::string::npos);
    }
}

TEST(SectionHeaders, MakeHeader) {
    EXPECT_EQ(section::MakeHeader("x"), "<<<x>>>\n");
    EXPECT_EQ(section::MakeHeader("x", ','), "<<<x:sep(44)>>>\n");
    EXPECT_EQ(section::MakeHeader("x", '\t'), "<<<x:sep(9)>>>\n");
    EXPECT_EQ(section::MakeHeader("x", '\0'), "<<<x>>>\n");
    EXPECT_EQ(section::MakeHeader("", '\0'), "<<<nothing>>>\n");
}

TEST(SectionHeaders, MakeSubSectionHeader) {
    EXPECT_EQ(section::MakeSubSectionHeader("x"), "[x]\n");
    EXPECT_EQ(section::MakeSubSectionHeader(""), "[nothing]\n");
}
TEST(SectionHeaders, MakeEmptyHeader) {
    EXPECT_EQ(section::MakeEmptyHeader(), "<<<>>>\n");
}

TEST(SectionHeaders, MakeLocalHeader) {
    EXPECT_EQ(section::MakeLocalHeader(), "<<<local:sep(0)>>>\n");
}
}  // namespace cma::provider
