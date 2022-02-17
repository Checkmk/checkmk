// test-service.cpp

//
#include "pch.h"

#include <filesystem>

#include "agent_controller.h"
#include "cfg.h"
#include "test_tools.h"

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
              fmt::format("x daemon -P {}", port));
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
              fmt::format("x daemon -P {} -A {}", port, allowed));
}

TEST(AgentController, FabricConfig) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    EXPECT_TRUE(ac::IsRunController(cfg::GetLoadedConfig()));
    EXPECT_TRUE(ac::IsUseLegacyMode(cfg::GetLoadedConfig()));
}

TEST(AgentController, ConfigApi) {
    auto cfg =
        YAML::Load("system:\n  controller:\n    run: yes\n    legacy: yes\n");
    EXPECT_TRUE(ac::IsRunController(cfg));
    EXPECT_TRUE(ac::IsUseLegacyMode(cfg));
}

TEST(AgentController, ConfigApiDefaults) {
    auto cfg = YAML::Load("system:\n");
    EXPECT_FALSE(ac::IsRunController(cfg));
    EXPECT_FALSE(ac::IsUseLegacyMode(cfg));
}

TEST(AgentController, EnableLegacyMode) {
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    ASSERT_FALSE(fs::exists(temp_fs->data() / ac::kLegacyPullFile));
    ac::EnableLegacyMode(true);
    ASSERT_TRUE(fs::exists(temp_fs->data() / ac::kLegacyPullFile));
    ac::EnableLegacyMode(false);
    EXPECT_FALSE(fs::exists(temp_fs->data() / ac::kLegacyPullFile));
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
