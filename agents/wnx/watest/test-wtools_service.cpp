// test-wtools.cpp
// windows mostly

#include "pch.h"

#include <ranges>

#include "common/wtools.h"
#include "common/wtools_service.h"
#include "watest/test_tools.h"
#include "wnx/cma_core.h"
#include "wnx/windows_service_api.h"

using namespace std::string_literals;

namespace rs = std::ranges;

namespace wtools {

TEST(WtoolsService, Ctor) {
    WinService ws_main(cma::srv::kServiceName);
    if (!ws_main.isOpened()) {
        GTEST_SKIP();
    }

    WinService ws_double = std::move(ws_main);
    EXPECT_FALSE(ws_main.isOpened());
    EXPECT_TRUE(ws_double.isOpened());

    WinService ws_again(cma::srv::kServiceName);
    EXPECT_TRUE(ws_again.isOpened());
    {
        WinService ws(L"no such service");
        EXPECT_FALSE(ws.isOpened());
    }
}

namespace {
void CheckThe(const SERVICE_FAILURE_ACTIONS *x,
              const std::vector<int> &values) {
    ASSERT_EQ(x->cActions, 3);
    EXPECT_EQ(x->lpCommand, nullptr);
    EXPECT_EQ(x->lpRebootMsg, nullptr);
    EXPECT_TRUE(x->dwResetPeriod > 0);
    for (unsigned i = 0; i < x->cActions; ++i) {
        auto &a = x->lpsaActions[i];
        EXPECT_TRUE(a.Delay > 0);
        EXPECT_TRUE(
            rs::any_of(values, [a](int value) { return a.Type == value; }));
    }
}
}  // namespace

class WtoolsServiceFunc : public ::testing::Test {
protected:
    // original values from the registry
    uint32_t save_ec_{0};
    uint32_t save_start_{0};
    uint32_t save_delayed_{0};

public:
    wtools::WinService ws_{cma::srv::kServiceName};
    static constexpr std::pair<uint32_t, WinService::ErrorMode> checks_ec_[]{
        {SERVICE_ERROR_IGNORE, WinService::ErrorMode::ignore},
        {SERVICE_ERROR_NORMAL, WinService::ErrorMode::log}};

    static constexpr std::string_view name_ec_ = WinService::kRegErrorControl;
    static constexpr std::string_view name_start_ = "Start";
    static constexpr std::string_view name_delayed_ = "DelayedAutoStart";

    const std::wstring reg_path_ =
        ConvertToUtf16(WinService::pathToRegistry(cma::srv::kServiceName));

    void SetUp() override {
        save_ec_ = WinService::readUint32(cma::srv::kServiceName, name_ec_);
        save_start_ =
            WinService::readUint32(cma::srv::kServiceName, name_start_);
        save_delayed_ =
            WinService::readUint32(cma::srv::kServiceName, name_delayed_);
    }

    void TearDown() override {
        if (save_ec_ !=
            WinService::readUint32(cma::srv::kServiceName, name_ec_)) {
            for (auto c : checks_ec_) {
                if (c.first == save_ec_) {
                    ws_.configureError(c.second);
                    break;
                }
            }
        }
        if (save_start_ !=
            WinService::readUint32(cma::srv::kServiceName, name_start_)) {
            SetRegistryValue(reg_path_, ConvertToUtf16(name_start_),
                             save_start_);
        }

        if (save_delayed_ !=
            WinService::readUint32(cma::srv::kServiceName, name_delayed_)) {
            SetRegistryValue(reg_path_, ConvertToUtf16(name_delayed_),
                             save_delayed_);
        }
    }
};

TEST_F(WtoolsServiceFunc, ConfigServiceRestart) {
    if (!ws_.isOpened()) {
        GTEST_SKIP();
    }
    ws_.configureRestart(true);
    std::pair<int, bool> checks[] = {{SC_ACTION_NONE, false},
                                     {SC_ACTION_RESTART, true}};
    for (auto c : checks) {
        ASSERT_TRUE(ws_.configureRestart(c.second));
        auto x = ws_.GetServiceFailureActions();
        SCOPED_TRACE("check restart");
        CheckThe(x.get(), {c.first});
    }
}

TEST_F(WtoolsServiceFunc, ConfigServiceErrorControl) {
    if (!ws_.isOpened()) {
        GTEST_SKIP();
    }
    //
    //

    ASSERT_EQ(name_ec_, "ErrorControl");
    ASSERT_EQ(WinService::kRegStart, "Start");

    if (!rs::any_of(checks_ec_,
                    [this](auto check) { return check.first == save_ec_; }))
        GTEST_SKIP() << "bad value start " << save_ec_ << "in registry";

    for (auto c : checks_ec_) {
        ASSERT_TRUE(ws_.configureError(c.second));
        EXPECT_EQ(WinService::readUint32(cma::srv::kServiceName, name_ec_),
                  c.first);
    }
}

TEST_F(WtoolsServiceFunc, ConfigService) {
    if (!ws_.isOpened()) {
        GTEST_SKIP();
    }

    struct CheckSet {
        uint32_t reg_value_main;
        uint32_t reg_value_delayed;
        WinService::StartMode mode;
    } checks[] = {{SERVICE_DISABLED, 0, WinService::StartMode::disabled},
                  {SERVICE_DEMAND_START, 0, WinService::StartMode::stopped},
                  {SERVICE_AUTO_START, 0, WinService::StartMode::started},
                  {SERVICE_AUTO_START, 1, WinService::StartMode::delayed}};

    if (!rs::any_of(checks, [this](auto check) {
            return check.reg_value_main == save_start_;
        }))
        GTEST_SKIP() << "bad value start " << save_start_ << "in registry";

    for (auto c : checks) {
        ASSERT_TRUE(ws_.configureStart(c.mode));
        EXPECT_EQ(WinService::readUint32(cma::srv::kServiceName, name_start_),
                  c.reg_value_main);
        EXPECT_EQ(WinService::readUint32(cma::srv::kServiceName, name_delayed_),
                  c.reg_value_delayed);
    }
}
}  // namespace wtools
