// test-wtools.cpp
// windows mostly

#include "pch.h"

#include "cma_core.h"
#include "common/wtools.h"
#include "common/wtools_service.h"
#include "test_tools.h"
#include "windows_service_api.h"

namespace wtools {

TEST(WtoolsService, Ctor) {
    WinService ws_main(cma::srv::kServiceName);
    if (!ws_main.isOpened()) {
        GTEST_SKIP();
    }

    auto h = ws_main.handle_;
    WinService ws_double = std::move(ws_main);
    EXPECT_FALSE(ws_main.isOpened());
    EXPECT_TRUE(ws_double.isOpened());
    EXPECT_EQ(h, ws_double.handle_);

    WinService ws_again(cma::srv::kServiceName);
    EXPECT_TRUE(ws_again.isOpened());
    EXPECT_NE(ws_again.handle_, ws_double.handle_);
}

static void CheckThe(const SERVICE_FAILURE_ACTIONS* x,
                     const std::vector<int>& values) {
    ASSERT_EQ(x->cActions, 3);
    EXPECT_EQ(x->lpCommand, nullptr);
    EXPECT_EQ(x->lpRebootMsg, nullptr);
    EXPECT_TRUE(x->dwResetPeriod > 0);
    for (unsigned i = 0; i < x->cActions; ++i) {
        auto& a = x->lpsaActions[i];
        EXPECT_TRUE(a.Delay > 0);
        EXPECT_TRUE(std::any_of(std::begin(values), std::end(values),
                                // predicate:
                                [a](int value) { return a.Type == value; }));
    }
}

TEST(WtoolsService, All) {
    WinService ws_main(cma::srv::kServiceName);
    if (ws_main.handle_ == nullptr) {
        GTEST_SKIP();
        return;
    }
    //
    //
    {
        WinService ws(L"no such service");
        ASSERT_EQ(ws.handle_, nullptr);
        EXPECT_FALSE(ws.isOpened());
    }

    {
        WinService ws(cma::srv::kServiceName);
        if (ws.handle_ == nullptr)
            GTEST_SKIP() << "This is NOT VALID SITUATION";
        ASSERT_TRUE(ws.isOpened());

        ws.configureRestart(true);
        {
            std::pair<int, bool> checks[] = {{SC_ACTION_NONE, false},
                                             {SC_ACTION_RESTART, true}};
            for (auto c : checks) {
                ASSERT_TRUE(ws.configureRestart(c.second));
                auto x = ws.GetServiceFailureActions();
                SCOPED_TRACE("check restart");
                CheckThe(x.get(), {c.first});
            }
        }
        // log
        {
            constexpr std::string_view name = WinService::kRegErrorControl;
            ASSERT_EQ(name, "ErrorControl");
            ASSERT_EQ(WinService::kRegStart, "Start");
            auto sav = WinService::ReadUint32(cma::srv::kServiceName, name);
            std::pair<uint32_t, WinService::ErrorMode> checks[] = {
                {SERVICE_ERROR_IGNORE, WinService::ErrorMode::ignore},
                {SERVICE_ERROR_NORMAL, WinService::ErrorMode::log}};

            if (!std::any_of(std::begin(checks), std::end(checks),
                             [sav](auto check) { return check.first == sav; }))
                GTEST_SKIP() << "bad value start " << sav << "in registry";

            ON_OUT_OF_SCOPE(if (sav != WinService::ReadUint32(
                                           cma::srv::kServiceName, name)) {
                for (auto c : checks) {
                    if (c.first == sav) {
                        ws.configureError(c.second);
                        break;
                    }
                }
            });

            for (auto c : checks) {
                ASSERT_TRUE(ws.configureError(c.second));
                EXPECT_EQ(WinService::ReadUint32(cma::srv::kServiceName, name),
                          c.first);
            }
        }
        // start
        {
            constexpr std::string_view name = "Start";
            auto sav = WinService::ReadUint32(cma::srv::kServiceName, name);

            std::pair<uint32_t, WinService::StartMode> checks[] = {
                {SERVICE_DISABLED, WinService::StartMode::disabled},
                {SERVICE_DEMAND_START, WinService::StartMode::stopped},
                {SERVICE_AUTO_START, WinService::StartMode::started}};

            if (!std::any_of(std::begin(checks), std::end(checks),
                             [sav](auto check) { return check.first == sav; }))
                GTEST_SKIP() << "bad value start " << sav << "in registry";

            ON_OUT_OF_SCOPE(if (sav != WinService::ReadUint32(
                                           cma::srv::kServiceName, name)) {
                for (auto c : checks) {
                    if (c.first == sav) {
                        ws.configureStart(c.second);
                        break;
                    }
                }
            });

            for (auto c : checks) {
                ASSERT_TRUE(ws.configureStart(c.second));
                EXPECT_EQ(WinService::ReadUint32(cma::srv::kServiceName, name),
                          c.first);
            }
        }
    }
}

}  // namespace wtools
