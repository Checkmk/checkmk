// carrier test
//

#include "pch.h"

#include "wnx/carrier.h"
#include "wnx/cfg.h"
#include "wnx/commander.h"
#include "common/mailslot_transport.h"
#include "wnx/service_processor.h"

using namespace std::chrono_literals;

namespace cma::commander {

static bool GetEnabledFlag(bool dflt) {
    auto yaml = cfg::GetLoadedConfig();
    auto yaml_global = yaml[cfg::groups::kGlobal];
    return cfg::GetVal(yaml_global, cfg::vars::kEnabled, dflt);
}

static void SetEnabledFlag(bool flag) {
    auto yaml = cfg::GetLoadedConfig();
    auto yaml_global = yaml[cfg::groups::kGlobal];
    yaml_global[cfg::vars::kEnabled] = flag;
}

TEST(Commander, Base) {
    auto yaml = cfg::GetLoadedConfig();
    auto yaml_global = yaml[cfg::groups::kGlobal];
    EXPECT_TRUE(yaml_global[cfg::vars::kEnabled].IsScalar());
    auto enabled = cfg::GetVal(yaml_global, cfg::vars::kEnabled, false);
    ASSERT_TRUE(enabled);
    SetEnabledFlag(false);
    enabled = cfg::GetVal(yaml_global, cfg::vars::kEnabled, true);
    ASSERT_FALSE(enabled);
    RunCommand("a", kReload);
    EXPECT_FALSE(enabled);
    RunCommand(kMainPeer, "aa");
    EXPECT_FALSE(enabled);

    RunCommand(kMainPeer, "aa");
    EXPECT_FALSE(enabled);

    EXPECT_NO_THROW(RunCommand("", ""));
    RunCommand(kMainPeer, kReload);
    enabled = GetEnabledFlag(false);
    EXPECT_TRUE(enabled);
    SetEnabledFlag(false);

    mailslot::Slot mailbox(
        mailslot::BuildCustomMailSlotName("WinAgentTestLocal", 0, "."));
    using namespace cma::carrier;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    cma::srv::ServiceProcessor processor;
    mailbox.ConstructThread(
        cma::srv::SystemMailboxCallback, 20, &processor,
        wtools::SecurityLevel::admin);  // admin is intentional
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());
    cma::tools::sleep(100ms);

    cma::carrier::CoreCarrier cc;
    // "mail"
    auto ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret);
    cc.sendCommand(kMainPeer, "a");
    cma::tools::sleep(100ms);
    enabled = GetEnabledFlag(true);
    EXPECT_FALSE(enabled);
    cc.sendCommand(kMainPeer, kReload);
    cma::tools::sleep(100ms);

    enabled = GetEnabledFlag(false);
    EXPECT_TRUE(enabled);

    cc.shutdownCommunication();
}
}  // namespace cma::commander

namespace cma::commander {  // to become friendly for wtools classes

TEST(Commander, RunCommandDefault) {
    EXPECT_FALSE(RunCommand("", kPassTrue));
    EXPECT_TRUE(RunCommand(kMainPeer, kPassTrue));
    EXPECT_FALSE(RunCommand(kMainPeer, ""));
    EXPECT_FALSE(RunCommand(kMainPeer, "invalidcommand"));
    EXPECT_TRUE(RunCommand(kMainPeer, kReload));
    EXPECT_FALSE(RunCommand(kMainPeer, kUninstallAlert));
}

TEST(Commander, GetSet) {
    ASSERT_TRUE(ObtainRunCommandProcessor() != nullptr);
    auto saved_rcp = ObtainRunCommandProcessor();
    ASSERT_TRUE(saved_rcp == RunCommand);
    ON_OUT_OF_SCOPE(ChangeRunCommandProcessor(saved_rcp));
    ChangeRunCommandProcessor(nullptr);
    EXPECT_TRUE(ObtainRunCommandProcessor() == nullptr);
    ChangeRunCommandProcessor(nullptr);
}

}  // namespace cma::commander
