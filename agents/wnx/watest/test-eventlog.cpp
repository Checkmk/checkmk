// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <filesystem>

#include "common/wtools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

#include "cfg.h"

#include "providers/logwatch_event.h"
#include "providers/logwatch_event_details.h"

#include "service_processor.h"
// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <filesystem>

#include "common/wtools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

#include "cfg.h"

#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogstd.h"
#include "eventlog/eventlogvista.h"

namespace cma::evl {

TEST(EventLogTest, Base) {
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
        auto [last, str] =
            PrintEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit, false);
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(!str.empty());
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
        auto [last, str] =
            PrintEventLog(*ptr, 0, cma::cfg::EventLevels::kCrit, false);
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(!str.empty());
    }
}

}  // namespace cma::evl
