// test-service.cpp

//
#include "pch.h"

#include "agent_controller.h"
#include "cfg.h"
#include "test_tools.h"

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
}  // namespace cma::ac
