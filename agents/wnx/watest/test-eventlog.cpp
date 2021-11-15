// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <filesystem>

#include "cfg.h"
#include "cfg_engine.h"
#include "common/wtools.h"
#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogstd.h"
#include "eventlog/eventlogvista.h"
#include "providers/logwatch_event.h"
#include "providers/logwatch_event_details.h"
#include "service_processor.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::evl {

TEST(EventLogTest, ChoosePos) {
    EXPECT_EQ(choosePos(1), 2);
    EXPECT_EQ(choosePos(cfg::kFromBegin), 0);
}

TEST(EventLogTest, ScanEventLogIntegration) {
    for (auto vista_mode : {false, true}) {
        auto ptr = OpenEvl(L"Application", vista_mode);
        ASSERT_TRUE(ptr != nullptr);
        auto [last, level] = ScanEventLog(*ptr, 0, cfg::EventLevels::kCrit);
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(level > cfg::EventLevels::kAll);
    }
}

TEST(EventLogTest, PrintEventLog) {
    for (auto vista_mode : {false, true}) {
        auto ptr = OpenEvl(L"Application", vista_mode);
        ASSERT_TRUE(ptr != nullptr);

        std::string str;
        auto last = PrintEventLog(*ptr, 0, cfg::EventLevels::kCrit, false,
                                  [&str](const std::string& in) -> bool {
                                      str += in;
                                      return str.length() <
                                             (cfg::logwatch::kMaxSize / 10);
                                  });
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(!str.empty());
        {
            std::string str;
            auto last = PrintEventLog(*ptr, 0, cfg::EventLevels::kCrit, false,
                                      [&str](const std::string& in) -> bool {
                                          str += in;
                                          return str.length() < 100 ||
                                                 str.length() > 10'000;
                                      });
            EXPECT_TRUE(last > 0);
            EXPECT_TRUE(str.size() >= 100);
            EXPECT_TRUE(str.size() < 12'000);  // approximately
        }
    }
}

TEST(EventLogTest, BeginningOfTheLog) {  // check empty log
    {
        auto ptr = OpenEvl(L"HardwareEvents", false);
        ASSERT_TRUE(ptr != nullptr);

        std::string str;
        auto last = PrintEventLog(*ptr, cfg::kFromBegin, cfg::EventLevels::kAll,
                                  false, [&str](const std::string& in) -> bool {
                                      str += in;
                                      return true;
                                  });
        EXPECT_TRUE(last == cfg::kFromBegin);
        EXPECT_TRUE(str.empty());
    }

    {
        auto ptr = OpenEvl(L"Application", false);
        ASSERT_TRUE(ptr != nullptr);

        std::string str;
        auto last = PrintEventLog(*ptr, cfg::kFromBegin, cfg::EventLevels::kAll,
                                  false, [&str](const std::string& in) -> bool {
                                      str += in;
                                      return false;
                                  });
        EXPECT_TRUE(last >= 0);
        EXPECT_FALSE(str.empty());
    }
}

}  // namespace cma::evl
