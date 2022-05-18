// test-service.cpp

//
#include "pch.h"

#include "common/wtools.h"
#include "firewall.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "windows_service_api.h"

using namespace std::chrono_literals;

namespace wtools {  // to become friendly for wtools classes
class TestProcessor : public wtools::BaseServiceProcessor {
public:
    TestProcessor() { s_counter++; }
    virtual ~TestProcessor() { s_counter--; }

    // Standard Windows API to Service hit here
    void stopService() { stopped_ = true; }
    void startService() { started_ = true; }
    void pauseService() { paused_ = true; }
    void continueService() { continued_ = true; }
    void shutdownService() { shutdowned_ = true; }
    const wchar_t *getMainLogName() const { return L"log.log"; }
    void preContextCall() { pre_context_call_ = true; }

    bool stopped_ = false;
    bool started_ = false;
    bool paused_ = false;
    bool shutdowned_ = false;
    bool continued_ = false;
    bool pre_context_call_ = false;
    static int s_counter;
};  // namespace wtoolsclassTestProcessor:publiccma::srv::BaseServiceProcessor
int TestProcessor::s_counter = 0;

TEST(ServiceControllerTest, CreateDelete) {
    using namespace std::chrono;
    {
        wtools::ServiceController controller(std::make_unique<TestProcessor>());
        EXPECT_EQ(TestProcessor::s_counter, 1);
        auto p = dynamic_cast<TestProcessor *>(controller.processor_.get());
        ASSERT_NE(nullptr, p);
        EXPECT_FALSE(p->started_ || p->continued_ || p->paused_ ||
                     p->shutdowned_ || p->stopped_);
        EXPECT_NE(controller.processor_, nullptr);
        EXPECT_EQ(controller.name_, nullptr);
        EXPECT_EQ(controller.can_stop_, false);
        EXPECT_EQ(controller.can_shutdown_, false);
        EXPECT_EQ(controller.can_pause_continue_, false);
        EXPECT_NE(controller.processor_, nullptr);
    }
    EXPECT_EQ(TestProcessor::s_counter, 0);
    EXPECT_EQ(ServiceController::s_controller_, nullptr);
}

static constexpr const wchar_t *const test_service_name = L"CmkTestService";

TEST(ServiceControllerTest, InstallUninstall) {
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio).w("Skip Test - you have to be elevated");
        return;
    }

    auto ret = wtools::InstallService(test_service_name,  // name of service
                                      L"Test Name",  // service name to display
                                      SERVICE_DEMAND_START,  // start type
                                      nullptr,               // dependencies
                                      nullptr,               // no account
                                      nullptr                // no password
    );
    EXPECT_TRUE(ret);
    wtools::UninstallService(test_service_name,
                             wtools::UninstallServiceMode::test);
}

TEST(ServiceControllerTest, StartStop) {
    int counter = 0;

    wtools::ServiceController controller(
        std::make_unique<cma::srv::ServiceProcessor>(100ms, [&counter]() {
            counter++;
            return true;
        }));
    EXPECT_NE(controller.processor_, nullptr);
    EXPECT_EQ(controller.name_, nullptr);
    EXPECT_EQ(controller.can_stop_, false);
    EXPECT_EQ(controller.can_shutdown_, false);
    EXPECT_EQ(controller.can_pause_continue_, false);
    EXPECT_NE(controller.processor_, nullptr);

    wtools::UninstallService(test_service_name);
    ASSERT_TRUE(wtools::InstallService(test_service_name,  // name of service
                                       L"Test Name",  // service name to display
                                       SERVICE_DEMAND_START,  // start type
                                       nullptr,               // dependencies
                                       nullptr,               // no account
                                       nullptr                // no password
                                       ));
    ON_OUT_OF_SCOPE(wtools::UninstallService(test_service_name));
    auto success = wtools::ServiceController::StopType::fail;
    std::thread t([&]() {
        success =
            controller.registerAndRun(test_service_name, true, true, true);
    });
    if (t.joinable()) {
        t.join();
    }

    EXPECT_EQ(success, wtools::ServiceController::StopType::no_connect);
    EXPECT_EQ(counter, 0);
}

}  // namespace wtools

namespace cma::srv {
extern bool g_global_stop_signaled;
TEST(SelfConfigure, Checker) {
    auto handle = SelfOpen();
    if (handle == nullptr) {
        xlog::sendStringToStdio(
            "No test self configuration, agent is not installed",
            xlog::internal::Colors::yellow);
        return;
    }
    ON_OUT_OF_SCOPE(CloseServiceHandle(handle));

    EXPECT_NO_THROW(IsServiceConfigured(handle));
    EXPECT_NO_THROW(SelfConfigure());  //
    EXPECT_TRUE(IsServiceConfigured(handle));
}

TEST(CmaSrv, GlobalApi) {
    EXPECT_FALSE(cma::srv::IsGlobalStopSignaled());
    ServiceProcessor sp;
    sp.stopService();
    EXPECT_TRUE(cma::srv::IsGlobalStopSignaled());
    g_global_stop_signaled = false;
}

static void SetStartMode(std::string_view mode) {
    using namespace cma::cfg;
    auto cfg = cma::cfg::GetLoadedConfig();
    cfg[groups::kSystem] =
        YAML::Load(fmt::format("service:\n  start_mode: {}\n", mode));
}

static void SetRestartOnCrash(bool restart) {
    using namespace cma::cfg;
    auto cfg = cma::cfg::GetLoadedConfig();
    cfg[groups::kSystem] = YAML::Load(fmt::format(
        "service:\n  restart_on_crash: {}\n", restart ? "yes" : "no"));
}

static void SetErrorMode(std::string_view mode) {
    using namespace cma::cfg;
    auto cfg = cma::cfg::GetLoadedConfig();
    cfg[groups::kSystem] =
        YAML::Load(fmt::format("service:\n  error_mode: {}\n", mode));
}

static YAML::Node GetServiceNode() {
    using namespace cma::cfg;
    auto cfg = GetLoadedConfig();
    auto os = GetNode(cfg, groups::kSystem);
    return GetNode(os, vars::kService);
}

static std::string GetServiceStart(const std::string &dflt) {
    using namespace cma::cfg;
    auto service = GetServiceNode();

    return GetVal(service, vars::kStartMode, dflt);
}

static bool GetServiceRestart(bool dflt) {
    using namespace cma::cfg;
    auto service = GetServiceNode();

    return GetVal(service, vars::kRestartOnCrash, dflt);
}

static std::string GetServiceError(const std::string &dflt) {
    using namespace cma::cfg;
    auto service = GetServiceNode();

    return GetVal(service, vars::kErrorMode, dflt);
}

TEST(CmaSrv, ServiceConfig) {
    using namespace cma::cfg;
    using namespace wtools;
    OnStartTest();
    ON_OUT_OF_SCOPE(OnStartTest());

    EXPECT_EQ(std::string(defaults::kErrorMode), values::kErrorModeLog);
    EXPECT_EQ(defaults::kRestartOnCrash, true);
    EXPECT_EQ(std::string(defaults::kStartMode), values::kStartModeAuto);

    //
    {
        // first mode, second config text
        std::pair<WinService::StartMode, std::string_view> pairs[] = {
            {WinService::StartMode::started, values::kStartModeAuto},
            {WinService::StartMode::started, "invalid"},  // check bad value
            {WinService::StartMode::delayed, values::kStartModeDelayed},
            {WinService::StartMode::stopped, values::kStartModeDemand},
            {WinService::StartMode::disabled, values::kStartModeDisabled}};

        for (auto p : pairs) {
            SetStartMode(p.second);
            auto cfg = GetServiceStart("a");
            EXPECT_EQ(cfg, p.second);
            EXPECT_EQ(GetServiceStartModeFromCfg(cfg), p.first);
        }
    }
    {
        std::pair<WinService::ErrorMode, std::string_view> pairs[] = {
            {WinService::ErrorMode::log, values::kErrorModeLog},
            {WinService::ErrorMode::ignore, values::kErrorModeIgnore}};

        for (auto p : pairs) {
            SetErrorMode(p.second);
            auto cfg = GetServiceError("b");
            EXPECT_EQ(cfg, p.second);
            EXPECT_EQ(GetServiceErrorModeFromCfg(cfg), p.first);
        }
    }

    {
        bool bools[] = {false, true};

        for (auto b : bools) {
            SetRestartOnCrash(b);
            auto cfg = GetServiceRestart(!b);
            EXPECT_EQ(cfg, b);
        }
    }
}

TEST(CmaSrv, ServiceChange) {
    using namespace cma::cfg;
    using namespace wtools;

    ASSERT_EQ(std::string(values::kErrorModeIgnore), "ignore");
    ASSERT_EQ(std::string(values::kErrorModeLog), "log");

    OnStartTest();
    if (!ProcessServiceConfiguration(cma::srv::kServiceName))
        GTEST_SKIP() << "service either not installed or not admin";

    ON_OUT_OF_SCOPE(OnStartTest();
                    ProcessServiceConfiguration(cma::srv::kServiceName););

    auto err_control =
        WinService::ReadUint32(kServiceName, WinService::kRegErrorControl);
    // setting opposite value
    SetErrorMode(err_control == 0 ? values::kErrorModeLog
                                  : values::kErrorModeIgnore);
    ProcessServiceConfiguration(cma::srv::kServiceName);
    auto new_err_control =
        WinService::ReadUint32(kServiceName, WinService::kRegErrorControl);
    EXPECT_EQ(new_err_control, err_control == SERVICE_ERROR_IGNORE
                                   ? SERVICE_ERROR_NORMAL
                                   : SERVICE_ERROR_IGNORE);

    auto start = WinService::ReadUint32(kServiceName, WinService::kRegStart);
    if (start <= SERVICE_AUTO_START)
        SetStartMode(values::kStartModeDemand);
    else
        SetStartMode(values::kStartModeAuto);
    ProcessServiceConfiguration(cma::srv::kServiceName);
    auto new_start =
        WinService::ReadUint32(kServiceName, WinService::kRegStart);
    EXPECT_EQ(new_start, start < SERVICE_AUTO_START ? SERVICE_AUTO_START
                                                    : SERVICE_DEMAND_START);
}

namespace {
void SetCfgMode(YAML::Node &cfg, std::string_view mode) {
    cfg[cfg::groups::kSystem] =
        YAML::Load(fmt::format("firewall:\n  mode: {}\n", mode));
}

void SetCfgMode(YAML::Node &cfg, std::string_view mode, bool all_ports) {
    cfg[cfg::groups::kSystem] =
        YAML::Load(fmt::format("firewall:\n  mode: {}\n  port: {}\n", mode,
                               all_ports ? "all" : "auto"));
}

std::wstring getPortValue(std::wstring_view name, std::wstring_view app_name) {
    auto rule = cma::fw::FindRule(name, app_name);
    ON_OUT_OF_SCOPE(if (rule) rule->Release());
    if (rule == nullptr) return {};

    BSTR bstr = nullptr;
    auto x = rule->get_LocalPorts(&bstr);
    std::wstring port(bstr);
    ::SysFreeString(bstr);
    return port;
}
}  // namespace

TEST(CmaSrv, FirewallIntegration) {
    auto test_fs = tst::TempCfgFs::CreateNoIo();
    ASSERT_TRUE(test_fs->loadFactoryConfig());
    auto cfg = cma::cfg::GetLoadedConfig();
    constexpr std::wstring_view app_name = L"test.exe.exe";

    auto fw_node = cfg::GetNode(cfg::groups::kSystem, cfg::vars::kFirewall);
    auto value = cfg::GetVal(fw_node, cfg::vars::kFirewallMode, std::string{});
    EXPECT_EQ(value, cfg::values::kModeConfigure);

    // remove all from the Firewall
    SetCfgMode(cfg, cfg::values::kModeRemove);
    fw_node = cfg::GetNode(cfg::groups::kSystem, cfg::vars::kFirewall);
    value = cfg::GetVal(fw_node, cfg::vars::kFirewallMode, std::string{});
    EXPECT_EQ(value, cfg::values::kModeRemove);
    ProcessFirewallConfiguration(app_name, GetFirewallPort(),
                                 srv::kTstFirewallRuleName);

    SetCfgMode(cfg, cfg::values::kModeConfigure, false);
    for (auto i = 0; i < 2; ++i) {
        ProcessFirewallConfiguration(app_name, GetFirewallPort(),
                                     srv::kTstFirewallRuleName);
        auto count = cma::fw::CountRules(kTstFirewallRuleName, app_name);
        EXPECT_EQ(count, 1);
        auto p = getPortValue(kTstFirewallRuleName, app_name);
        EXPECT_TRUE(p == L"6556");
    }

    SetCfgMode(cfg, cfg::values::kModeConfigure, true);
    for (auto i = 0; i < 2; ++i) {
        ProcessFirewallConfiguration(app_name, GetFirewallPort(),
                                     srv::kTstFirewallRuleName);
        auto count = cma::fw::CountRules(kTstFirewallRuleName, app_name);
        EXPECT_EQ(count, 1);
        auto p = getPortValue(kTstFirewallRuleName, app_name);
        EXPECT_TRUE(p == L"*");
    }

    SetCfgMode(cfg, cfg::values::kModeNone);
    for (auto i = 0; i < 2; ++i) {
        ProcessFirewallConfiguration(app_name, GetFirewallPort(),
                                     srv::kTstFirewallRuleName);
        auto count = cma::fw::CountRules(kTstFirewallRuleName, app_name);
        EXPECT_EQ(count, 1);
    }

    SetCfgMode(cfg, cfg::values::kModeRemove);
    for (auto i = 0; i < 2; ++i) {
        ProcessFirewallConfiguration(app_name, GetFirewallPort(),
                                     srv::kTstFirewallRuleName);
        auto count = cma::fw::CountRules(kTstFirewallRuleName, app_name);
        EXPECT_EQ(count, 0);
    }

    SetCfgMode(cfg, cfg::values::kModeNone);
    ProcessFirewallConfiguration(app_name, GetFirewallPort(),
                                 srv::kTstFirewallRuleName);
    EXPECT_EQ(0, cma::fw::CountRules(cma::srv::kTstFirewallRuleName, app_name));
}

}  // namespace cma::srv
