// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <psapi.h>

#include <chrono>
#include <condition_variable>
#include <mutex>
#include <thread>

#include "common/wtools.h"
#include "logger.h"
using namespace std::chrono_literals;

struct ThreadControlBlock {
    std::condition_variable cv;
    std::mutex lock;
    bool stop = false;
};

static ThreadControlBlock bad;
static ThreadControlBlock ctrl;
static std::vector<std::unique_ptr<char>> bad_vector;
void BadThreadFoo() {
    while (true) {
        bad_vector.emplace_back(new char[20'000'000]);
        auto data = bad_vector.back().get();
        memset(data, 1, 20'000'000);
        std::unique_lock lk(bad.lock);
        auto stop_time = std::chrono::steady_clock::now() + 200ms;
        const auto stopped =
            bad.cv.wait_until(lk, stop_time, [] { return bad.stop; });
        if (stopped || bad_vector.size() > 100) {
            break;
        }
    }
    bad_vector.clear();
}

void ControlThreadFoo() {
    while (true) {
        auto sz = wtools::GetOwnVirtualSize();
        XLOG::l("sz = [{}]", sz);
        if (!wtools::monitor::IsAgentHealthy()) {
            bad.stop = true;
        }

        std::unique_lock lk(ctrl.lock);
        auto stop_time = std::chrono::steady_clock::now() + 100ms;
        const auto stopped =
            ctrl.cv.wait_until(lk, stop_time, [] { return ctrl.stop; });
        if (stopped) {
            break;
        }
    }
}

namespace wtools {
TEST(HealthState, Monitor) {
    ctrl.stop = false;
    auto control_thread = std::thread(ControlThreadFoo);
    bad.stop = false;
    auto bad_thread = std::thread(BadThreadFoo);
    ASSERT_TRUE(bad_thread.joinable());
    if (bad_thread.joinable()) bad_thread.join();
    EXPECT_TRUE(bad.stop);
    ctrl.stop = true;
    if (control_thread.joinable()) control_thread.join();
    XLOG::SendStringToStdio("HealthState,Monitor:end\n", XLOG::Colors::cyan);
}
}  // namespace wtools
