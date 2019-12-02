// carrier test
//

#include "pch.h"

#include "carrier.h"
#include "cfg.h"
#include "commander.h"
#include "common/mailslot_transport.h"
#include "logger.h"
#include "service_processor.h"

namespace cma::commander {
bool RunCommand(std::string_view peer, std::string_view cmd);

static bool GetEnabledFlag(bool dflt) {
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    return cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, true);
}

static void SetEnabledFlag(bool flag) {
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    yaml_global[cma::cfg::vars::kEnabled] = flag;
}

TEST(Commander, Base) {
    using namespace std::chrono;
    //
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    EXPECT_TRUE(yaml_global[cma::cfg::vars::kEnabled].IsScalar());
    auto enabled =
        cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, false);
    ASSERT_TRUE(enabled);
    SetEnabledFlag(false);
    enabled = cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, true);
    ASSERT_FALSE(enabled);
    cma::commander::RunCommand("a", cma::commander::kReload);
    EXPECT_FALSE(enabled);
    cma::commander::RunCommand(cma::commander::kMainPeer, "aa");
    EXPECT_FALSE(enabled);

    cma::commander::RunCommand(cma::commander::kMainPeer, "aa");
    EXPECT_FALSE(enabled);

    EXPECT_NO_THROW(cma::commander::RunCommand("", ""));
    cma::commander::RunCommand(cma::commander::kMainPeer,
                               cma::commander::kReload);
    enabled = GetEnabledFlag(false);
    EXPECT_TRUE(enabled);
    SetEnabledFlag(false);

    cma::MailSlot mailbox("WinAgentTestLocal", 0);
    using namespace cma::carrier;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    cma::srv::ServiceProcessor processor;
    mailbox.ConstructThread(cma::srv::SystemMailboxCallback, 20, &processor);
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());
    cma::tools::sleep(100ms);

    cma::carrier::CoreCarrier cc;
    // "mail"
    auto ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret);
    cc.sendCommand(cma::commander::kMainPeer, "a");
    cma::tools::sleep(100ms);
    enabled = GetEnabledFlag(true);
    EXPECT_FALSE(enabled);
    cc.sendCommand(cma::commander::kMainPeer, cma::commander::kReload);
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
    ASSERT_TRUE(saved_rcp == cma::commander::RunCommand);
    ON_OUT_OF_SCOPE(ChangeRunCommandProcessor(saved_rcp));
    ChangeRunCommandProcessor(nullptr);
    EXPECT_TRUE(ObtainRunCommandProcessor() == nullptr);
    ChangeRunCommandProcessor(nullptr);
}

}  // namespace cma::commander
