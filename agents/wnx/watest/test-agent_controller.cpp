// test-service.cpp

//
#include "pch.h"

#include <filesystem>

#include "agent_controller.h"
#include "cfg.h"
#include "test_tools.h"

using namespace std::chrono_literals;
namespace fs = std::filesystem;
namespace cma::details {
extern bool g_is_service;
}

namespace cma::ac {
TEST(AgentController, StartAgent) {
    EXPECT_FALSE(ac::StartAgentController("cmd.exe"));
}

TEST(AgentController, KillAgent) {
    EXPECT_FALSE(ac::KillAgentController("anything"));
}

constexpr std::string_view port{"1111"};
constexpr std::string_view allowed{"::1 111.11.11/11 8.8.8.8"};
TEST(AgentController, BuildCommandLine) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(
        temp_fs->loadContent(fmt::format("global:\n"
                                         "  enabled: yes\n"
                                         "  only_from: \n"
                                         "  port: {}\n",
                                         port)));
    EXPECT_EQ(wtools::ToUtf8(ac::BuildCommandLine(fs::path("x"))),
              fmt::format("x daemon -P {} -vv", port));
}

TEST(AgentController, BuildCommandLineAllowed) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(
        temp_fs->loadContent(fmt::format("global:\n"
                                         "  enabled: yes\n"
                                         "  only_from: {}\n"
                                         "  port: {}\n",
                                         allowed, port)));
    EXPECT_EQ(wtools::ToUtf8(ac::BuildCommandLine(fs::path("x"))),
              fmt::format("x daemon -P {} -A {} -vv", port, allowed));
}

TEST(AgentController, LegacyMode) {
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    EXPECT_FALSE(ac::IsInLegacyMode());
    tst::CreateTextFile(fs::path{cfg::GetUserDir()} / ac::kLegacyPullFile,
                        "test");
    EXPECT_TRUE(ac::IsInLegacyMode());
}

TEST(AgentController, FabricConfig) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    EXPECT_TRUE(ac::IsRunController(cfg::GetLoadedConfig()));
}

TEST(AgentController, ConfigApi) {
    auto cfg = YAML::Load("system:\n  controller:\n    run: yes\n");
    EXPECT_TRUE(ac::IsRunController(cfg));
}

TEST(AgentController, ConfigApiDefaults) {
    auto cfg = YAML::Load("system:\n");
    EXPECT_FALSE(ac::IsRunController(cfg));
}

TEST(AgentController, CreateLegacyModeFile) {
    constexpr std::string_view marker_2_1 =
        "Check MK monitoring and management Service - 2.1, 64-bit";
    constexpr std::string_view marker_1_6_2_0 =
        "Check MK monitoring and management Service, 64-bit";

    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    auto marker_file = temp_fs->data() / ac::kCmkAgentUnistall;
    ASSERT_FALSE(fs::exists(temp_fs->data() / ac::kLegacyPullFile));

    // absent
    EXPECT_FALSE(ac::CreateLegacyModeFile(""));
    EXPECT_FALSE(fs::exists(temp_fs->data() / ac::kLegacyPullFile));

    // 2.1+
    tst::CreateTextFile(temp_fs->data() / ac::kCmkAgentUnistall, marker_2_1);
    EXPECT_FALSE(ac::CreateLegacyModeFile(marker_file));
    EXPECT_FALSE(fs::exists(temp_fs->data() / ac::kLegacyPullFile));
    EXPECT_FALSE(fs::exists(temp_fs->data() / ac::kCmkAgentUnistall));

    // old file
    tst::CreateTextFile(marker_file, marker_1_6_2_0);
    auto timestamp = fs::last_write_time(marker_file);
    fs::last_write_time(marker_file, timestamp - 11s);
    EXPECT_FALSE(ac::CreateLegacyModeFile(marker_file));
    EXPECT_FALSE(fs::exists(temp_fs->data() / ac::kLegacyPullFile));
    EXPECT_FALSE(fs::exists(temp_fs->data() / ac::kCmkAgentUnistall));

    // 1.6..2.0
    tst::CreateTextFile(marker_file, marker_1_6_2_0);
    EXPECT_TRUE(ac::CreateLegacyModeFile(marker_file));
    EXPECT_TRUE(fs::exists(temp_fs->data() / ac::kLegacyPullFile));
    EXPECT_FALSE(fs::exists(temp_fs->data() / ac::kCmkAgentUnistall));
}

TEST(AgentController, SimulationIntegration) {
    details::g_is_service = true;
    ON_OUT_OF_SCOPE(details::g_is_service = false;);
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    fs::copy(fs::path{"c:\\windows\\system32\\whoami.exe"},
             temp_fs->root() / cfg::files::kAgentCtl);
    const auto service = fs::path{cfg::GetRootDir()} / "cmd.exe";
    const auto expected =
        fs::path{cfg::GetUserBinDir()} / cfg::files::kAgentCtl;
    EXPECT_TRUE(ac::StartAgentController(service));
    EXPECT_TRUE(fs::exists(expected));
    EXPECT_TRUE(ac::KillAgentController(service));
    EXPECT_FALSE(fs::exists(expected));
}
}  // namespace cma::ac
