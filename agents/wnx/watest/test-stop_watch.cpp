// test-wtools.cpp
// windows mostly

#include "pch.h"

#include "common/stop_watch.h"
#include "tools/_misc.h"

namespace wtools {  // to become friendly for cma::cfg classes

TEST(Wtools, StopWatch) {
    using namespace std::chrono;
    StopWatch sw;
    EXPECT_EQ(sw.getUsCount(), 0);
    EXPECT_EQ(sw.getLastUsCount(), 0);
    EXPECT_EQ(sw.getCount(), 0);
    EXPECT_EQ(sw.isStarted(), false);

    auto ret = sw.stop();
    EXPECT_EQ(ret, 0);
    EXPECT_EQ(sw.getUsCount(), 0);
    EXPECT_EQ(sw.getLastUsCount(), 0);
    EXPECT_EQ(sw.getCount(), 0);
    EXPECT_EQ(sw.isStarted(), false);
    EXPECT_EQ(sw.check(), 0);
    auto pos = sw.pos_;
    EXPECT_TRUE(pos.time_since_epoch().count() == 0);

    sw.start();
    pos = sw.pos_;
    EXPECT_EQ(sw.getUsCount(), 0);
    EXPECT_EQ(sw.getCount(), 0);
    EXPECT_EQ(sw.isStarted(), true);
    EXPECT_TRUE(pos.time_since_epoch().count() != 0);
    auto check1 = sw.check();

    cma::tools::sleep(10ms);
    auto check2 = sw.check();

    EXPECT_NE(check2, 0);
    EXPECT_TRUE(check2 > check1);
    EXPECT_TRUE(sw.pos_ == pos);
    EXPECT_EQ(sw.getUsCount(), 0);
    EXPECT_EQ(sw.getLastUsCount(), 0);
    EXPECT_EQ(sw.getCount(), 0);
    EXPECT_EQ(sw.isStarted(), true);

    sw.start();
    EXPECT_TRUE(sw.pos_ == pos);
    auto stop_val = sw.stop();

    EXPECT_TRUE(sw.getUsCount() > 5000);
    EXPECT_EQ(sw.getUsCount(), stop_val);
    EXPECT_EQ(sw.getLastUsCount(), stop_val);
    EXPECT_EQ(sw.getCount(), 1);
    EXPECT_EQ(sw.isStarted(), false);

    {
        sw.started_ = true;
        auto sw1 = sw;
        EXPECT_EQ(sw1.getUsCount(), sw.getUsCount());
        EXPECT_EQ(sw1.getCount(), sw.getCount());
        EXPECT_EQ(sw1.isStarted(), false);
        sw.started_ = false;
    }

    {
        sw.started_ = true;
        auto sw1(sw);
        EXPECT_EQ(sw1.getUsCount(), sw.getUsCount());
        EXPECT_EQ(sw1.getCount(), sw.getCount());
        EXPECT_EQ(sw1.isStarted(), false);
        EXPECT_EQ(sw1.pos_,
                  std::chrono::time_point<std::chrono::steady_clock>());
        sw.started_ = false;

        sw1.started_ = true;
        auto sw2 = std::move(sw1);
        EXPECT_EQ(sw2.getUsCount(), sw.getUsCount());
        EXPECT_EQ(sw2.getCount(), sw.getCount());
        EXPECT_EQ(sw2.isStarted(), false);
        EXPECT_EQ(sw2.pos_,
                  std::chrono::time_point<std::chrono::steady_clock>());

        EXPECT_EQ(sw1.getUsCount(), 0);
        EXPECT_EQ(sw1.getCount(), 0);
        EXPECT_EQ(sw1.isStarted(), false);
        EXPECT_EQ(sw1.pos_,
                  std::chrono::time_point<std::chrono::steady_clock>());
    }

    sw.reset();
    EXPECT_TRUE(sw.getUsCount() == 0);
    EXPECT_EQ(sw.getCount(), 0);
}

}  // namespace wtools
