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
    auto pos = sw.pos();
    EXPECT_TRUE(pos.time_since_epoch().count() == 0);

    sw.start();
    pos = sw.pos();
    EXPECT_EQ(sw.getUsCount(), 0);
    EXPECT_EQ(sw.getCount(), 0);
    EXPECT_EQ(sw.isStarted(), true);
    EXPECT_TRUE(pos.time_since_epoch().count() != 0);
    auto check1 = sw.check();

    cma::tools::sleep(10ms);
    auto check2 = sw.check();

    EXPECT_NE(check2, 0);
    EXPECT_TRUE(check2 > check1);
    EXPECT_TRUE(sw.pos() == pos);
    EXPECT_EQ(sw.getUsCount(), 0);
    EXPECT_EQ(sw.getLastUsCount(), 0);
    EXPECT_EQ(sw.getCount(), 0);
    EXPECT_EQ(sw.isStarted(), true);

    sw.start();
    EXPECT_TRUE(sw.pos() == pos);
    auto stop_val = sw.stop();

    EXPECT_TRUE(sw.getUsCount() > 5000);
    EXPECT_EQ(sw.getUsCount(), stop_val);
    EXPECT_EQ(sw.getLastUsCount(), stop_val);
    EXPECT_EQ(sw.getCount(), 1);
    EXPECT_EQ(sw.isStarted(), false);

    {
        auto sw1 = sw;
        EXPECT_EQ(sw1.getUsCount(), sw.getUsCount());
        EXPECT_EQ(sw1.getCount(), sw.getCount());
        EXPECT_EQ(sw1.isStarted(), false);
    }

    {
        auto sw1(sw);
        EXPECT_EQ(sw1.getUsCount(), sw.getUsCount());
        EXPECT_EQ(sw1.getCount(), sw.getCount());
        EXPECT_EQ(sw1.isStarted(), false);
        EXPECT_EQ(sw1.pos(),
                  std::chrono::time_point<std::chrono::steady_clock>());
        auto sw2 = std::move(sw1);
        EXPECT_EQ(sw2.getUsCount(), sw.getUsCount());
        EXPECT_EQ(sw2.getCount(), sw.getCount());
        EXPECT_EQ(sw2.isStarted(), false);
        EXPECT_EQ(sw2.pos(),
                  std::chrono::time_point<std::chrono::steady_clock>());

        EXPECT_EQ(sw1.getUsCount(), 0);
        EXPECT_EQ(sw1.getCount(), 0);
        EXPECT_EQ(sw1.isStarted(), false);
        EXPECT_EQ(sw1.pos(),
                  std::chrono::time_point<std::chrono::steady_clock>());
    }

    sw.reset();
    EXPECT_TRUE(sw.getUsCount() == 0);
    EXPECT_EQ(sw.getCount(), 0);

    {
        StopWatch sw;
        sw.start();
        pos = sw.pos();
        sw.skip();
        EXPECT_TRUE(sw.pos() == pos);
        EXPECT_FALSE(sw.isStarted());
    }
}

}  // namespace wtools
