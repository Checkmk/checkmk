// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <filesystem>
#include <vector>

#include "cfg.h"
#include "cfg_engine.h"
#include "common/wtools.h"
#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogstd.h"
#include "eventlog/eventlogvista.h"
#include "providers/logwatch_event.h"
#include "providers/logwatch_event_details.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

using namespace std::string_literals;

namespace cma::evl {

namespace {
using Level = cma::evl::EventLogRecordBase::Level;
const std::vector<tst::EventRecordData> application_log_data{
    {13, 0x11, 0, L"Source"s, L"Message 1"s, Level::audit_failure},
    {13, 0x11, 1, L"Source"s, L"Message 2"s, Level::audit_success},
    {13, 0x11, 2, L"Source"s, L"Message 3"s, Level::error},
    {13, 0x11, 3, L"Source"s, L"Message 4"s, Level::information},
    {13, 0x11, 4, L"Source"s, L"Message 5"s, Level::success},
    {13, 0x11, 5, L"Source"s, L"Message 6"s, Level::warning}};
}  // namespace

const std::vector<tst::EventRecordData> &ApplicationLogData() {
    return application_log_data;
}

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

TEST(EventLogTest, PrintEventLogSkip) {
    EventLogDebug evd(tst::SimpleLogData());
    std::vector<std::string> table;
    auto last =
        PrintEventLog(evd, cfg::kFromBegin, cfg::EventLevels::kCrit, false,
                      SkipDuplicatedRecords::yes, [&](const auto &in) {
                          table.emplace_back(in);
                          return true;
                      });
    EXPECT_EQ(last, tst::SimpleLogData().size() - 1);
    EXPECT_EQ(table.size(), 5);
    EXPECT_EQ(fmt::format(kSkippedMessageFormat, 1), table[1]);
    EXPECT_EQ(fmt::format(kSkippedMessageFormat, 2), table[4]);
}

TEST(EventLogTest, PrintEventLogOneLine) {
    EventLogDebug evd(ApplicationLogData());
    for (auto vista_mode : {false, true}) {
        std::string str;
        auto last = PrintEventLog(
            evd, cfg::kFromBegin, cfg::EventLevels::kCrit, false,
            SkipDuplicatedRecords::no, [&str](const std::string &in) -> bool {
                str += in;
                return in.find(
                           wtools::ToUtf8(ApplicationLogData()[0].message)) !=
                       std::string::npos;
            });
        EXPECT_EQ(last, 1);
        EXPECT_NE(str.find(wtools::ToUtf8(ApplicationLogData()[0].message)),
                  std::string::npos);
    }
}

TEST(EventLogTest, PrintEventLogAll) {
    EventLogDebug evd(ApplicationLogData());
    for (auto vista_mode : {false, true}) {
        std::vector<std::string> table;
        auto last = PrintEventLog(evd, cfg::kFromBegin, cfg::EventLevels::kCrit,
                                  false, SkipDuplicatedRecords::no,
                                  [&](const std::string &in) -> bool {
                                      table.emplace_back(in);
                                      return true;
                                  });
        EXPECT_EQ(last, ApplicationLogData().size() - 1);
        EXPECT_EQ(table.size(), ApplicationLogData().size());
    }
}

TEST(EventLogTest, PrintEventLogOffset) {
    EventLogDebug evd(ApplicationLogData());
    for (auto vista_mode : {false, true}) {
        std::vector<std::string> table;
        auto last = PrintEventLog(evd, 2, cfg::EventLevels::kCrit, false,
                                  SkipDuplicatedRecords::no,
                                  [&](const std::string &in) -> bool {
                                      table.emplace_back(in);
                                      return true;
                                  });
        EXPECT_EQ(last, ApplicationLogData().size() - 1);
        EXPECT_EQ(table.size(), ApplicationLogData().size() - 3);
    }
}

TEST(EventLogTest, PrintEventLogIntegration) {
    for (auto vista_mode : {false, true}) {
        auto ptr = OpenEvl(L"Application", vista_mode);
        ASSERT_TRUE(ptr != nullptr);

        std::string str;
        auto last = PrintEventLog(
            *ptr, 0, cfg::EventLevels::kCrit, false, SkipDuplicatedRecords::no,
            [&str](const std::string &in) -> bool {
                str += in;
                return str.length() < (cfg::logwatch::kMaxSize / 10);
            });
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(!str.empty());
        {
            std::string str;
            auto last = PrintEventLog(*ptr, 0, cfg::EventLevels::kCrit, false,
                                      SkipDuplicatedRecords::no,
                                      [&str](const std::string &in) -> bool {
                                          str += in;
                                          return str.length() < 10'000;
                                      });
            EXPECT_TRUE(last > 0);
            EXPECT_TRUE(str.size() >= 100);
        }
    }
}

TEST(EventLogTest, BeginningOfTheHardwareLogIntegration) {
    auto ptr = OpenEvl(L"HardwareEvents", false);
    std::string str;
    auto last = PrintEventLog(*ptr, cfg::kFromBegin, cfg::EventLevels::kAll,
                              false, SkipDuplicatedRecords::no,
                              [&str](const std::string &in) -> bool {
                                  str += in;
                                  return true;
                              });
    EXPECT_TRUE(last == cfg::kFromBegin);
    EXPECT_TRUE(str.empty());
}

TEST(EventLogTest, BeginningOfTheApplicationLogIntegration) {
    auto ptr = OpenEvl(L"Application", false);
    std::string str;
    auto last = PrintEventLog(*ptr, cfg::kFromBegin, cfg::EventLevels::kAll,
                              false, SkipDuplicatedRecords::no,
                              [&str](const std::string &in) -> bool {
                                  str += in;
                                  return false;
                              });
    EXPECT_TRUE(last >= 0);
    EXPECT_FALSE(str.empty());
}

}  // namespace cma::evl
