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

TEST(EventLogTest, Base) {
    {
        EXPECT_EQ(choosePos(1), 2);
        EXPECT_EQ(choosePos(cma::cfg::kFromBegin), 0);
    }

    {
        auto ptr = OpenEvl(L"Application", false);
        ASSERT_TRUE(ptr != nullptr);
    }

    {
        auto ptr = OpenEvl(L"Application", false);
        ASSERT_TRUE(ptr != nullptr);
        auto [last, level] =
            ScanEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit);
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(level > cma::cfg::EventLevels::kAll);
    }

    {
        auto ptr = OpenEvl(L"Application", false);
        ASSERT_TRUE(ptr != nullptr);
        auto [last, level] =
            ScanEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit);
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(level > cma::cfg::EventLevels::kAll);
    }

    {
        auto ptr = OpenEvl(L"Application", false);
        ASSERT_TRUE(ptr != nullptr);
        auto [last, level] =
            ScanEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit);
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(level > cma::cfg::EventLevels::kAll);
    }
    {
        auto ptr = OpenEvl(L"Application", false);
        ASSERT_TRUE(ptr != nullptr);

        std::string str;
        auto last = PrintEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit, false,
                                  [&str](const std::string& in) -> bool {
                                      str += in;
                                      return str.length() <
                                             cma::cfg::logwatch::kMaxSize;
                                  });
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(!str.empty());
        {
            std::string str;
            auto last =
                PrintEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit, false,
                              [&str](const std::string& in) -> bool {
                                  str += in;
                                  return str.length() < 100;
                              });
            EXPECT_TRUE(last > 0);
            EXPECT_TRUE(str.size() >= 100);
            EXPECT_TRUE(str.size() < 2000);  // approximately
            EXPECT_TRUE(!str.empty());
        }
    }
}

TEST(EventLogTest, BeginningOfTheLog) {  // check empty log
    {
        auto ptr = OpenEvl(L"HardwareEvents", false);
        ASSERT_TRUE(ptr != nullptr);

        std::string str;
        auto last = PrintEventLog(*ptr, cma::cfg::kFromBegin,
                                  cma::cfg::EventLevels::kAll, false,
                                  [&str](const std::string& in) -> bool {
                                      str += in;
                                      return true;
                                  });
        EXPECT_TRUE(last == cma::cfg::kFromBegin);
        EXPECT_TRUE(str.empty());
    }

    {
        auto ptr = OpenEvl(L"Application", false);
        ASSERT_TRUE(ptr != nullptr);

        std::string str;
        auto last = PrintEventLog(*ptr, cma::cfg::kFromBegin,
                                  cma::cfg::EventLevels::kAll, false,
                                  [&str](const std::string& in) -> bool {
                                      str += in;
                                      return false;
                                  });
        EXPECT_TRUE(last >= 0);
        EXPECT_FALSE(str.empty());
    }
}

TEST(EventLogTest, Vista) {
    {
        auto ptr = OpenEvl(L"Application", true);
        ASSERT_TRUE(ptr != nullptr);
        auto [last, level] =
            ScanEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit);
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(level > cma::cfg::EventLevels::kAll);
    }
    {
        auto ptr = OpenEvl(L"Application", false);
        ASSERT_TRUE(ptr != nullptr);
        std::string str;
        auto last = PrintEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit, false,
                                  [&str](const std::string& in) -> bool {
                                      str += in;
                                      return str.length() <
                                             cma::cfg::logwatch::kMaxSize;
                                  });
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(!str.empty());
        {
            std::string str;
            auto last =
                PrintEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit, false,
                              [&str](const std::string& in) -> bool {
                                  str += in;
                                  return str.length() < 100;
                              });
            EXPECT_TRUE(last > 0);
            EXPECT_TRUE(str.size() >= 100);
            EXPECT_TRUE(str.size() < 2000);  // approximately
            EXPECT_TRUE(!str.empty());
        }
    }
}

}  // namespace cma::evl
