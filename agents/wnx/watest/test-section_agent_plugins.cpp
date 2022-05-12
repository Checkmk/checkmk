// test-section_ps.cpp
//
//
#include "pch.h"

#include <filesystem>
#include <ranges>

#include "cfg.h"
#include "common/wtools.h"
#include "providers/agent_plugins.h"
#include "test_tools.h"

namespace fs = std::filesystem;

namespace cma::provider {

class AgentPluginsTest : public ::testing::Test {
public:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        ASSERT_TRUE(temp_fs_->loadFactoryConfig());
    }

    std::vector<std::string> getRows() {
        cma::provider::AgentPlugins ap{provider::kAgentPlugins,
                                       provider::AgentPlugins::kSepChar};
        auto result = ap.generateContent();
        return tools::SplitString(result, "\n");
    }

    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(AgentPluginsTest, Empty) {
    auto rows = getRows();
    EXPECT_EQ(rows[0] + "\n", section::MakeHeader(section::kAgentPlugins));
    EXPECT_EQ(rows[1], fmt::format("pluginsdir {}",
                                   wtools::ToUtf8(cfg::GetUserPluginsDir())));
    EXPECT_EQ(rows[2],
              fmt::format("localdir {}", wtools::ToUtf8(cfg::GetLocalDir())));
}

TEST_F(AgentPluginsTest, File) {
    auto ps_file = fs::path{cfg::GetUserPluginsDir()} / "p.ps1";
    tst::CreateTextFile(ps_file,
                        "#\n"
                        "$CMK_VERSION = \"2.2.0i1\"\n");
    auto rows = getRows();
    EXPECT_EQ(rows.size(), 4);
    EXPECT_EQ(rows[0] + "\n", section::MakeHeader(section::kAgentPlugins));
    EXPECT_EQ(rows[1], fmt::format("pluginsdir {}",
                                   wtools::ToUtf8(cfg::GetUserPluginsDir())));
    EXPECT_EQ(rows[2],
              fmt::format("localdir {}", wtools::ToUtf8(cfg::GetLocalDir())));

    EXPECT_TRUE(std::ranges::any_of(rows, [&](const std::string &row) {
        return row == fmt::format("{}:CMK_VERSION = \"2.2.0i1\"", ps_file);
    }));
}

TEST_F(AgentPluginsTest, FileMix) {
    const std::vector<std::tuple<fs::path, std::string, std::string>> to_create = {
        {fs::path{cfg::GetUserPluginsDir()} / "p.ps1",
         "#\n"
         "$CMK_VERSION = {}\n",
         "\"2.2.0i1\""},
        {fs::path{cfg::GetUserPluginsDir()} / "p.bat",
         "@rem \n"
         "set CMK_VERSION={}\nxxxx\n",
         "\"2.2.0i1\""},
        {fs::path{cfg::GetUserPluginsDir()} / "p.vbs",
         "\n"
         "Const CMK_VERSION = {}\nxxxx\n",
         "\"2.2.0i1\""},
        {fs::path{cfg::GetLocalDir()} / "p.ps1",
         "#\n"
         "$CMK_VERSION = {}\n",
         "\"2.2.0i1\""},
        {fs::path{cfg::GetLocalDir()} / "p.cmd",
         "@rem \n"
         "set CMK_VERSION={}\nxxxx\n",
         "\"2.2.0i1\""},
        {fs::path{cfg::GetUserPluginsDir()} / "unversioned.ps1",
         "#\n",
         "unversioned"},
        {fs::path{cfg::GetLocalDir()} / "unversioned.cmd",
         "@rem \n",
         "unversioned"},
    };

    for (const auto [p, s, ver] : to_create) {
        tst::CreateTextFile(p, ((ver == "unversioned") ? s : fmt::format(s, ver)));
    }
    auto rows = getRows();
    EXPECT_EQ(rows.size(), to_create.size() + 3);
    EXPECT_EQ(rows[0] + "\n", section::MakeHeader(section::kAgentPlugins));
    EXPECT_EQ(rows[1], fmt::format("pluginsdir {}",
                                   wtools::ToUtf8(cfg::GetUserPluginsDir())));
    EXPECT_EQ(rows[2],
              fmt::format("localdir {}", wtools::ToUtf8(cfg::GetLocalDir())));

    for (const auto [p, _, ver] : to_create) {
        EXPECT_TRUE(std::ranges::any_of(rows, [&](const std::string &row) {
            return row == fmt::format("{}:CMK_VERSION = {}", p, ver);
        }));
    }
}

}  // namespace cma::provider
