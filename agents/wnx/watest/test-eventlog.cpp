// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <filesystem>
#include <vector>

#include "common/wtools.h"
#include "eventlog/eventlogbase.h"
#include "eventlog/eventlogvista.h"
#include "providers/logwatch_event_details.h"
#include "tools/_misc.h"
#include "tools/_raii.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"
#include "wnx/cfg_engine.h"
#include "wnx/service_processor.h"

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

namespace {
constexpr const wchar_t *kOwnSource = L"watest";
}  // namespace

/// For the tests that read the real Application log. They need a crit-level
/// record there, which a long-lived machine has but a fresh Windows may not:
/// write one only then, so that other machines' logs stay untouched.
class EventLogApplicationTest : public ::testing::Test {
protected:
    static void SetUpTestSuite() {
        const auto log = OpenEvl(L"Application", false);
        ASSERT_TRUE(log->isLogValid());
        const auto [last_before, worst] =
            ScanEventLog(*log, 0, cfg::EventLevels::kCrit);
        if (worst == cfg::EventLevels::kCrit) {
            return;
        }

        auto *source = ::RegisterEventSourceW(nullptr, kOwnSource);
        ASSERT_NE(source, nullptr);
        ON_OUT_OF_SCOPE(::DeregisterEventSource(source));
        const std::wstring message =
            L"watest EventLogApplicationTest record, written by the test "
            L"itself so that the Application log has error-level content to "
            L"read";
        const wchar_t *strings[] = {message.c_str()};
        ASSERT_TRUE(::ReportEventW(source, EVENTLOG_ERROR_TYPE, 0, 100, nullptr,
                                   1, 0, strings, nullptr));

        // Look for our own source: other programs may write to the
        // Application log meanwhile.
        const auto own_record_visible = [&log, from = last_before + 1] {
            log->seek(from);
            while (true) {
                const EventLogRecordBase::ptr record{log->readRecord()};
                if (!record) {
                    return false;
                }
                if (record->source() == kOwnSource) {
                    return true;
                }
            }
        };
        ASSERT_TRUE(tst::WaitForSuccessSilent(std::chrono::seconds{5},
                                              own_record_visible))
            << "the record written is not in the log";
    }
};

TEST(EventLogTest, ChoosePos) {
    EXPECT_EQ(choosePos(1), 2);
    EXPECT_EQ(choosePos(cfg::kFromBegin), 0);
}

TEST_F(EventLogApplicationTest, ScanEventLogComponent) {
    for (auto vista_mode : {false, true}) {
        auto ptr = OpenEvl(L"Application", vista_mode);
        ASSERT_TRUE(ptr != nullptr);
        auto [last, level] = ScanEventLog(*ptr, 0, cfg::EventLevels::kCrit);
        EXPECT_TRUE(last > 0);
        EXPECT_EQ(level, cfg::EventLevels::kCrit);
    }
}

TEST(EventLogTest, PrintEventLogSkip) {
    EventLogDebug evd(tst::SimpleLogData());
    std::vector<std::string> table;
    auto last = PrintEventLog(
        evd, cfg::kFromBegin, cfg::EventLevels::kCrit, cfg::EventContext::with,
        SkipDuplicatedRecords::yes,
        [&](const auto &in) {
            table.emplace_back(in);
            return true;
        },
        [](const auto *) { return true; });
    EXPECT_EQ(last, tst::SimpleLogData().size() - 1);
    EXPECT_EQ(table.size(), 5);
    EXPECT_EQ(fmt::format(kSkippedMessageFormat, 1), table[1]);
    EXPECT_EQ(fmt::format(kSkippedMessageFormat, 2), table[4]);
}

TEST(EventLogTest, PrintEventLogOneLine) {
    EventLogDebug evd(ApplicationLogData());
    std::string str;
    const auto last = PrintEventLog(
        evd, cfg::kFromBegin, cfg::EventLevels::kCrit, cfg::EventContext::with,
        SkipDuplicatedRecords::no,
        [&str](const std::string &in) {
            str += in;
            return in.find(wtools::ToUtf8(ApplicationLogData()[0].message)) !=
                   std::string::npos;
        },
        [](const auto *) { return true; });
    EXPECT_EQ(last, 1);
    EXPECT_NE(str.find(wtools::ToUtf8(ApplicationLogData()[0].message)),
              std::string::npos);
}

TEST(EventLogTest, PrintEventLogAll) {
    EventLogDebug evd(ApplicationLogData());
    std::vector<std::string> table;
    const auto last = PrintEventLog(
        evd, cfg::kFromBegin, cfg::EventLevels::kCrit, cfg::EventContext::with,
        SkipDuplicatedRecords::no,
        [&](const std::string &in) {
            table.emplace_back(in);
            return true;
        },
        [](const auto *) { return true; });
    EXPECT_EQ(last, ApplicationLogData().size() - 1);
    EXPECT_EQ(table.size(), ApplicationLogData().size());
}

TEST(EventLogTest, PrintEventLogOffset) {
    EventLogDebug evd(ApplicationLogData());
    std::vector<std::string> table;
    const auto last = PrintEventLog(
        evd, 2, cfg::EventLevels::kCrit, cfg::EventContext::with,
        SkipDuplicatedRecords::no,
        [&](const std::string &in) {
            table.emplace_back(in);
            return true;
        },
        [](const auto *) { return true; });
    EXPECT_EQ(last, ApplicationLogData().size() - 1);
    EXPECT_EQ(table.size(), ApplicationLogData().size() - 3);
}

TEST_F(EventLogApplicationTest, PrintEventLogComponent) {
    for (auto vista_mode : {false, true}) {
        auto ptr = OpenEvl(L"Application", vista_mode);
        ASSERT_TRUE(ptr != nullptr);

        std::string str;
        const auto last = PrintEventLog(
            *ptr, 0, cfg::EventLevels::kCrit, cfg::EventContext::with,
            SkipDuplicatedRecords::no,
            [&str](const std::string &in) {
                str += in;
                return str.length() < cfg::logwatch::kMaxSize / 10;
            },
            [](const auto *) { return true; });
        EXPECT_TRUE(last > 0);
        EXPECT_TRUE(!str.empty());
        {
            std::string str;
            auto last = PrintEventLog(
                *ptr, 0, cfg::EventLevels::kCrit, cfg::EventContext::with,
                SkipDuplicatedRecords::no,
                [&str](const std::string &in) {
                    str += in;
                    return str.length() < 10'000;
                },
                [](const auto *) { return true; });
            EXPECT_TRUE(last > 0);
            EXPECT_TRUE(str.size() >= 100);
        }
    }
}

TEST(EventLogTest, BeginningOfTheHardwareLogComponent) {
    auto ptr = OpenEvl(L"HardwareEvents", false);
    std::string str;
    const auto last = PrintEventLog(
        *ptr, cfg::kFromBegin, cfg::EventLevels::kAll, cfg::EventContext::with,
        SkipDuplicatedRecords::no,
        [&str](const std::string &in) {
            str += in;
            return true;
        },
        [](const auto *) { return true; });
    EXPECT_TRUE(last == cfg::kFromBegin);
    EXPECT_TRUE(str.empty());
}

TEST_F(EventLogApplicationTest, BeginningOfTheApplicationLogComponent) {
    auto ptr = OpenEvl(L"Application", false);
    std::string str;
    auto _ = PrintEventLog(
        *ptr, cfg::kFromBegin, cfg::EventLevels::kAll, cfg::EventContext::with,
        SkipDuplicatedRecords::no,
        [&str](const std::string &in) {
            str += in;
            return false;
        },
        [](const auto *) { return true; });
    EXPECT_FALSE(str.empty());
}

}  // namespace cma::evl
