// test-section_ps.cpp
//
//
#include "pch.h"

#include <filesystem>
#include <ranges>

#include "common/wtools.h"
#include "providers/agent_plugins.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"

namespace fs = std::filesystem;

namespace cma::provider {

class AgentPluginsTest : public ::testing::Test {
public:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        ASSERT_TRUE(temp_fs_->loadFactoryConfig());
    }

    [[nodiscard]] std::vector<std::string> getRows() const {
        AgentPlugins ap{kAgentPlugins, AgentPlugins::kSepChar};
        return tools::SplitString(ap.generateContent(), "\n");
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

TEST_F(AgentPluginsTest, JustExe) {
    auto ps_file = fs::path{cfg::GetUserPluginsDir()} / "empty.exe";
    tst::CreateTextFile(ps_file, "");
    auto rows = getRows();
    ASSERT_EQ(rows.size(), 4);
    EXPECT_TRUE(std::ranges::any_of(rows, [&](const std::string &row) {
        return row == fmt::format("{}:CMK_VERSION = n/a", ps_file);
    }));
}

TEST_F(AgentPluginsTest, DISABLED_Exe) {
    // Test is disabled because we need a binary to build: not appropriate for
    // unit testing. You may enable this test manually
    auto v_file = tst::GetSolutionRoot() / "test_files" / "tools" / "v" /
                  "target" / "release" / "v.exe";
    fs::copy(v_file, fs::path{cfg::GetUserPluginsDir()} / "mk-sql.exe");
    auto rows = getRows();
    ASSERT_EQ(rows.size(), 4);
    EXPECT_TRUE(rows[3].ends_with("v.exe:CMK_VERSION = \"0.1.0\""));
}

TEST_F(AgentPluginsTest, FileMix) {
    const std::vector<std::tuple<fs::path, std::string, std::string>>
        to_create = {
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
            {fs::path{cfg::GetUserPluginsDir()} / "unversioned.ps1", "#\n",
             "unversioned"},
            {fs::path{cfg::GetLocalDir()} / "unversioned.cmd", "@rem \n",
             "unversioned"},
            {fs::path{cfg::GetUserPluginsDir()} / "p.py",
             "#\n"
             "__version__ = {}\n",
             "\"2.2.0i1\""},
            {fs::path{cfg::GetLocalDir()} / "p.py",
             "#\n"
             "__version__ = {}\n",
             "\"2.2.0i1\""},
        };

    for (const auto &[p, s, ver] : to_create) {
        tst::CreateTextFile(
            p, ver == "unversioned" ? s : fmt::format(fmt::runtime(s), ver));
    }
    auto rows = getRows();
    EXPECT_EQ(rows.size(), to_create.size() + 3);
    EXPECT_EQ(rows[0] + "\n", section::MakeHeader(section::kAgentPlugins));
    EXPECT_EQ(rows[1], fmt::format("pluginsdir {}",
                                   wtools::ToUtf8(cfg::GetUserPluginsDir())));
    EXPECT_EQ(rows[2],
              fmt::format("localdir {}", wtools::ToUtf8(cfg::GetLocalDir())));

    for (const auto &[p, _, ver] : to_create) {
        EXPECT_TRUE(std::ranges::any_of(rows, [&](const std::string &row) {
            return row == fmt::format("{}:CMK_VERSION = {}", p, ver);
        }));
    }
}

}  // namespace cma::provider
