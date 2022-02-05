// test-service.cpp

//
#include "pch.h"

#include "agent_controller.h"

namespace cma::ac {
TEST(AgentController, StartAgent) {
    EXPECT_FALSE(ac::StartAgentController("cmd.exe"));
}

TEST(AgentController, KillAgent) { EXPECT_FALSE(ac::KillAgentController()); }
}  // namespace cma::ac
