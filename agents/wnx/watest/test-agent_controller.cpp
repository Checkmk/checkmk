// test-service.cpp

//
#include "pch.h"

#include <filesystem>

#include "agent_controller.h"
#include "cfg.h"
#include "test_tools.h"

namespace fs = std::filesystem;

namespace cma::ac {
TEST(AgentController, StartAgent) {
    EXPECT_FALSE(ac::StartAgentController("cmd.exe"));
}

TEST(AgentController, KillAgent) { EXPECT_FALSE(ac::KillAgentController()); }

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

}  // namespace cma::ac
