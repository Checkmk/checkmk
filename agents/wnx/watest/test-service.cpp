// test-service.cpp

//
#include "pch.h"

#include "common/wtools.h"
#include "service_processor.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "windows_service_api.h"

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
    const wchar_t* getMainLogName() const { return L"log.log"; }
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
        auto p = dynamic_cast<TestProcessor*>(controller.processor_.get());
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

static constexpr const wchar_t* const test_service_name = L"CmkTestService";

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
    using namespace cma::srv;
    using namespace std::chrono;
    int counter = 0;

    wtools::ServiceController controller(std::make_unique<ServiceProcessor>(
        100ms, [&counter](const void* Processor) {
            xlog::l("pip").print();
            counter++;
            return true;
        }));
    EXPECT_NE(controller.processor_, nullptr);
    EXPECT_EQ(controller.name_, nullptr);
    EXPECT_EQ(controller.can_stop_, false);
    EXPECT_EQ(controller.can_shutdown_, false);
    EXPECT_EQ(controller.can_pause_continue_, false);
    EXPECT_NE(controller.processor_, nullptr);

    // special case with "no connect" case
    {
        auto ret =
            wtools::InstallService(test_service_name,  // name of service
                                   L"Test Name",  // service name to display
                                   SERVICE_DEMAND_START,  // start type
                                   nullptr,               // dependencies
                                   nullptr,               // no account
                                   nullptr                // no password
            );
        EXPECT_TRUE(ret);

        if (ret) {
            ON_OUT_OF_SCOPE(wtools::UninstallService(test_service_name));
            auto success = wtools::ServiceController::StopType::fail;
            std::thread t([&]() {
                success = controller.registerAndRun(test_service_name, true,
                                                    true, true);
            });
            if (t.joinable()) t.join();

            EXPECT_EQ(success, wtools::ServiceController::StopType::no_connect);
            EXPECT_EQ(counter, 0);
        }
    }
}

}  // namespace wtools

TEST(Misc, All) {
    {
        std::string a = "a";
        cma::tools::AddDirSymbol(a);
        EXPECT_TRUE(a == "a\\");
        cma::tools::AddDirSymbol(a);
        EXPECT_TRUE(a == "a\\");
    }
    {
        std::string b = "b\\";
        cma::tools::AddDirSymbol(b);
        EXPECT_TRUE(b == "b\\");
        b = "b/";
        cma::tools::AddDirSymbol(b);
        EXPECT_TRUE(b == "b/");
    }
}

namespace cma::srv {
extern bool global_stop_signaled;
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
    global_stop_signaled = false;
}

}  // namespace cma::srv
