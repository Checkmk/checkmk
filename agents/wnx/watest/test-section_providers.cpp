// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include "cfg.h"
#include "common/version.h"
#include "common/wtools.h"
#include "providers/check_mk.h"
#include "providers/df.h"
#include "providers/internal.h"
#include "providers/logwatch_event.h"
#include "providers/mem.h"
#include "providers/mrpe.h"
#include "providers/ohm.h"
#include "providers/p_perf_counters.h"
#include "providers/plugins.h"
#include "providers/services.h"
#include "providers/skype.h"
#include "providers/wmi.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::provider {

static const std::string section_name{cma::section::kUseEmbeddedName};

class Empty : public Synchronous {
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
    EXPECT_EQ(plugins.getUniqName(), cma::section::kPlugins);
}

TEST(SectionProviders, LocalProviderConstruction) {
    LocalProvider local;
    EXPECT_EQ(local.getUniqName(), cma::section::kLocal);
}

TEST(SectionProviders, BasicUptime) {
    cma::srv::SectionProvider<cma::provider::UptimeSync> uptime_provider;
    EXPECT_EQ(uptime_provider.getEngine().getUniqName(),
              cma::section::kUptimeName);

    auto &e3 = uptime_provider.getEngine();
    auto uptime = e3.generateContent(section_name);
    ASSERT_TRUE(!uptime.empty());
    auto result = cma::tools::SplitString(uptime, "\n");
    EXPECT_EQ(result.size(), 2);
    EXPECT_EQ(result[0], "<<<uptime>>>");
    auto value = result[1].find_first_not_of("0123456789");
    EXPECT_EQ(value, std::string::npos);
}

TEST(SectionProviders, BasicDf) {
    cma::srv::SectionProvider<cma::provider::Df> df_provider;
    EXPECT_EQ(df_provider.getEngine().getUniqName(), cma::section::kDfName);

    auto &e2 = df_provider.getEngine();
    auto df = e2.generateContent(section_name);
    ASSERT_TRUE(!df.empty());
    auto result = cma::tools::SplitString(df, "\n");
    ASSERT_TRUE(result.size() > 1);
    EXPECT_EQ(result[0], "<<<df:sep(9)>>>");
    auto count = result.size();
    for (size_t i = 1; i < count; ++i) {
        auto values = cma::tools::SplitString(result[i], "\t");
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

class SectionProviderCheckMkFixture : public ::testing::Test {
public:
    static constexpr size_t core_lines_ = 20;
    static constexpr size_t full_lines_ = core_lines_ + 3;
    static constexpr std::string_view names_[] = {
        "Version",          "BuildDate",       "AgentOS",
        "Hostname",         "Architecture",    "WorkingDirectory",
        "ConfigFile",       "LocalConfigFile", "AgentDirectory",
        "PluginsDirectory", "StateDirectory",  "ConfigDirectory",
        "TempDirectory",    "LogDirectory",    "SpoolDirectory",
        "LocalDirectory",   "AgentController", "LegacyPullMode",
        "OnlyFrom"};

    static constexpr std::pair<std::string_view, std::string_view>
        only_from_cases_[] = {
            //
            {"~", ""},
            {"127.0.0.1", "127.0.0.1"},
            {"127.0.0.1 192.168.0.1", "127.0.0.1 192.168.0.1"},
            {"[127.0.0.1, 192.168.0.1]", "127.0.0.1 192.168.0.1"},
            {"[127.0.0.1, ::1]", "127.0.0.1 ::1"},
            {"[127.0.0.1/16, ::1/64]", "127.0.0.1/16 ::1/64"}
            //
        };

    std::string getContent() { return getEngine().generateContent(); }
    std::vector<std::string> getFullResultAsTable() {
        return tools::SplitString(getContent(), "\n");
    }
    std::vector<std::string> getCoreResultAsTable() {
        auto result = getFullResultAsTable();
        if (result.size() == full_lines_ &&
            result[core_lines_] + "\n" ==
                section::MakeHeader(section::kCheckMk)) {
            result.resize(core_lines_);
        }
        result.erase(result.begin());
        return result;
    }
    CheckMk &getEngine() { return check_mk_provider_.getEngine(); }

    YAML::Node getWorkingCfg() {
        if (!temp_fs_) {
            temp_fs_ = std::move(tst::TempCfgFs::CreateNoIo());
        }
        return cfg::GetLoadedConfig();
    }

    std::filesystem::path createDataDir() {
        if (!temp_fs_) {
            temp_fs_ = std::move(tst::TempCfgFs::Create());
        }
        return temp_fs_->data();
    }

    auto get_val(const std::string &raw) -> std::string {
        auto tbl = tools::SplitString(raw, ": ");
        if (tbl.size() == 2) {
            return tbl[1];
        }

        return {};
    };

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
    for (const auto &r : result) {
        auto values = tools::SplitString(r, ": ");
        EXPECT_EQ(values[0], std::string{*expected_name++});
        if (values[0] == "AgentController") {
            EXPECT_EQ(values.size(), 1);
        } else {
            EXPECT_EQ(values.size(), 2);
        }
    }
}

TEST_F(SectionProviderCheckMkFixture, AdvancedFields) {
    createDataDir();
    auto result = getCoreResultAsTable();
    EXPECT_EQ(get_val(result[0]), CHECK_MK_VERSION);
    EXPECT_EQ(get_val(result[2]), "windows");
    EXPECT_EQ(get_val(result[3]), cfg::GetHostName());
    EXPECT_EQ(get_val(result[4]), tgt::Is64bit() ? "64bit" : "32bit");
    EXPECT_EQ(result[16], "AgentController: ");
    EXPECT_EQ(result[17], "LegacyPullMode: yes");
    cfg::GetLoadedConfig()[cfg::groups::kSystem][cfg::vars::kController] =
        YAML::Load("legacy: no");
    result = getCoreResultAsTable();
    EXPECT_EQ(result[17], "LegacyPullMode: no");
}

TEST_F(SectionProviderCheckMkFixture, OnlyFromField) {
    createDataDir();
    auto cfg = cfg::GetLoadedConfig();

    for (auto p : only_from_cases_) {
        cfg[cfg::groups::kGlobal][cfg::vars::kOnlyFrom] =
            YAML::Load(std::string{p.first});
        auto result = getCoreResultAsTable();
        EXPECT_EQ(get_val(*std::prev(result.end())), std::string{p.second});
    }
}

TEST_F(SectionProviderCheckMkFixture, FailedInstall) {
    tst::misc::CopyFailedPythonLogFileToLog(createDataDir());

    auto result = getFullResultAsTable();
    EXPECT_TRUE(result[full_lines_ - 2].starts_with("UpdateFailed:"));
    EXPECT_TRUE(result[full_lines_ - 1].starts_with("UpdateRecoverAction:"));
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
        auto rows = cma::tools::SplitString(mem, "\n");
        header_ = rows[0];
        auto count = rows.size();
        for (size_t i = 1; i < count; ++i) {
            auto values = cma::tools::SplitString(rows[i], ":");
            cma::tools::LeftTrim(values[1]);
            auto sub_values = cma::tools::SplitString(values[1], " ");
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
TEST_F(SectionProvidersFixture, ServicesIntegration) {
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
