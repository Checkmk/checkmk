// test-section-providers.cpp

//
#include "pch.h"

#include "cfg.h"
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
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::provider {

static const std::string section_name{cma::section::kUseEmbeddedName};

TEST(SectionProvider, Construction) {
    PluginsProvider plugins;
    EXPECT_EQ(plugins.getUniqName(), cma::section::kPlugins);

    LocalProvider local;
    EXPECT_EQ(local.getUniqName(), cma::section::kLocal);
}

TEST(SectionProviders, BasicUptime) {
    using namespace cma::section;
    using namespace cma::provider;

    cma::srv::SectionProvider<Uptime> uptime_provider;
    EXPECT_EQ(uptime_provider.getEngine().getUniqName(), kUptimeName);

    auto& e3 = uptime_provider.getEngine();
    auto uptime = e3.generateContent(section_name);
    ASSERT_TRUE(!uptime.empty());
    auto result = cma::tools::SplitString(uptime, "\n");
    EXPECT_EQ(result.size(), 2);
    EXPECT_EQ(result[0], "<<<uptime>>>");
    auto value = result[1].find_first_not_of("0123456789");
    EXPECT_EQ(value, std::string::npos);
}

TEST(SectionProviders, BasicDf) {
    using namespace cma::section;
    using namespace cma::provider;

    cma::srv::SectionProvider<Df> df_provider;
    EXPECT_EQ(df_provider.getEngine().getUniqName(), kDfName);

    auto& e2 = df_provider.getEngine();
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

TEST(SectionProviders, BasicSystemTime) {
    using namespace cma::section;
    using namespace cma::provider;

    cma::srv::SectionProvider<SystemTime> system_time_provider;
    EXPECT_EQ(system_time_provider.getEngine().getUniqName(), kSystemTime);

    auto& e4 = system_time_provider.getEngine();
    auto system_time = e4.generateContent(section_name);
    ASSERT_TRUE(!system_time.empty());
    auto result = cma::tools::SplitString(system_time, "\n");
    EXPECT_EQ(result.size(), 2);
    EXPECT_EQ(result[0], "<<<systemtime>>>");
    auto value = result[1].find_first_not_of("0123456789");
    EXPECT_EQ(value, std::string::npos);
}

TEST(SectionProviders, BasicCheckMk) {
    using namespace cma::section;
    using namespace cma::provider;

    const char* array_of_names[] = {
        "Version",          "BuildDate",       "AgentOS",
        "Hostname",         "Architecture",    "WorkingDirectory",
        "ConfigFile",       "LocalConfigFile", "AgentDirectory",
        "PluginsDirectory", "StateDirectory",  "ConfigDirectory",
        "TempDirectory",    "LogDirectory",    "SpoolDirectory",
        "LocalDirectory",   "OnlyFrom"};

    cma::srv::SectionProvider<CheckMk> check_mk_provider;
    EXPECT_EQ(check_mk_provider.getEngine().getUniqName(), kCheckMk);
    auto& e1 = check_mk_provider.getEngine();
    auto cmk = e1.generateContent(section_name);
    ASSERT_TRUE(!cmk.empty());
    auto result = cma::tools::SplitString(cmk, "\n");
    EXPECT_EQ(result.size(), 18);
    EXPECT_EQ(result[0], "<<<check_mk>>>");

    auto count = result.size();
    for (size_t i = 1; i < count; ++i) {
        auto values = cma::tools::SplitString(result[i], ": ");
        EXPECT_EQ(values[0], array_of_names[i - 1]);
    }
}

TEST(SectionProviders, BasicServices) {
    using namespace cma::section;
    using namespace cma::provider;

    cma::srv::SectionProvider<Services> services_provider;
    EXPECT_EQ(services_provider.getEngine().getUniqName(), kServices);

    auto& e5 = services_provider.getEngine();
    auto sp = e5.generateContent(section_name);
    ASSERT_TRUE(!sp.empty());
    auto result = cma::tools::SplitString(sp, "\n");
    EXPECT_TRUE(result.size() > 20);
    EXPECT_EQ(result[0], "<<<services>>>");

    auto count = result.size();
    for (size_t i = 1; i < count; ++i) {
        auto values = cma::tools::SplitString(result[i], " ", 2);
        EXPECT_FALSE(values[0].empty());
        EXPECT_FALSE(values[1].empty());
        EXPECT_FALSE(values[2].empty());
        EXPECT_TRUE(values[1].find("/") != std::string::npos);
    }
}

TEST(SectionHeaders, All) {
    auto ret = cma::section::MakeHeader("x");
    EXPECT_EQ(ret, "<<<x>>>\n");

    ret = cma::section::MakeHeader("x", ',');
    EXPECT_EQ(ret, "<<<x:sep(44)>>>\n");

    ret = cma::section::MakeHeader("x", '\t');
    EXPECT_EQ(ret, "<<<x:sep(9)>>>\n");

    ret = cma::section::MakeHeader("x", '\0');
    EXPECT_EQ(ret, "<<<x>>>\n");

    ret = cma::section::MakeHeader("", '\0');
    EXPECT_EQ(ret, "<<<nothing>>>\n");

    ret = cma::section::MakeSubSectionHeader("x");
    EXPECT_EQ(ret, "[x]\n");

    ret = cma::section::MakeSubSectionHeader("");
    EXPECT_EQ(ret, "[nothing]\n");

    ret = cma::section::MakeEmptyHeader();
    EXPECT_EQ(ret, "<<<>>>\n");

    ret = cma::section::MakeLocalHeader();
    EXPECT_EQ(ret, "<<<local>>>\n");
}

}  // namespace cma::provider
