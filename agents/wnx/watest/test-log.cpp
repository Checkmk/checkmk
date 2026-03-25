// test-log.cpp :

#include "pch.h"

#include <filesystem>
#include <string>

#include "tools/_raii.h"
#include "watest/test_tools.h"
#include "wnx/cfg.h"
#include "wnx/logger.h"
#include "wnx/on_start.h"
#include "wnx/read_file.h"

namespace fs = std::filesystem;
using namespace std::string_literals;

namespace xlog {
TEST(xlogTest, xlogLowLevel) {
    EXPECT_TRUE(IsAddCrFlag(Flags::kAddCr));
    EXPECT_FALSE(IsAddCrFlag(~Flags::kAddCr));

    EXPECT_TRUE(IsNoCrFlag(Flags::kNoCr));
    EXPECT_FALSE(IsNoCrFlag(~Flags::kNoCr));

    std::string s;
    EXPECT_NO_THROW(RmCr(s));
    AddCr(s);
    EXPECT_EQ(s, "\n");
    AddCr(s);
    EXPECT_EQ(s, "\n");
    RmCr(s);
    EXPECT_EQ(s, "");
    EXPECT_NO_THROW(RmCr(s));
}
}  // namespace xlog

namespace XLOG {

namespace internal {
TEST(LogInternalTest, Type2MarkerCheck) {
    EXPECT_EQ(Type2Marker(xlog::Type::kDebugOut), XLOG::kWarning);
    EXPECT_EQ(Type2Marker(xlog::Type::kLogOut), XLOG::kError);
    EXPECT_EQ(Type2Marker(xlog::Type::kOtherOut), XLOG::kInfo);
    EXPECT_EQ(Type2Marker(xlog::Type::kVerboseOut), XLOG::kTrace);
}

TEST(LogInternalTest, Mods2DirectionsCheck) {
    xlog::LogParam lp{std::wstring{}};
    constexpr int mark = 0x1000'0000;
    lp.directions_ = mark;

    EXPECT_EQ(Mods2Directions(lp, Mods::kFile),
              mark | xlog::Directions::kFilePrint);
    EXPECT_EQ(Mods2Directions(lp, Mods::kStdio),
              mark | xlog::Directions::kStdioPrint);
    EXPECT_EQ(Mods2Directions(lp, Mods::kEvent),
              mark | xlog::Directions::kEventPrint);

    constexpr uint32_t all_mark = 0xFFFF'FFFF;
    lp.directions_ = all_mark;

    EXPECT_EQ(Mods2Directions(lp, Mods::kNoFile),
              all_mark & ~xlog::Directions::kFilePrint);
    EXPECT_EQ(Mods2Directions(lp, Mods::kNoStdio),
              all_mark & ~xlog::Directions::kStdioPrint);
    EXPECT_EQ(Mods2Directions(lp, Mods::kNoEvent),
              all_mark & ~xlog::Directions::kEventPrint);
}
}  // namespace internal

TEST(LogTest, RotationFileNameCreation) {
    EXPECT_NO_THROW(details::MakeBackupLogName("a", 0));
    EXPECT_EQ("a", details::MakeBackupLogName("a", 0));
    EXPECT_EQ("a.2", details::MakeBackupLogName("a", 2));
    EXPECT_EQ("a.5", details::MakeBackupLogName("a", 5));
}

TEST(LogTest, RotationFileCfgParam) {
    for (auto type : {XLOG::LogType::debug, XLOG::LogType::log,
                      XLOG::LogType::stdio, XLOG::LogType::trace}) {
        XLOG::Emitter e(type);
        const auto max_count = e.getBackupLogMaxCount();
        const auto max_size = e.getBackupLogMaxSize();
        EXPECT_TRUE(max_count < 32);
        EXPECT_TRUE(max_size > 100'000);
        EXPECT_TRUE(max_size < 1'000'000'000);
    }
}

static bool FindString(const std::string &name, unsigned int index,
                       const std::string &text) {
    auto filename = details::MakeBackupLogName(name, index);
    auto data = tst::ReadFileAsTable(filename);
    if (data.size() != 1) return false;
    auto table = cma::tools::SplitString(data[0], " ");
    if (table.size() != 3) return false;
    return table[2] == text;
}

TEST(LogTest, RotationFile) {
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());

    using namespace XLOG::details;
    fs::path log_file = cma::cfg::GetTempDir();
    log_file /= "log.log";

    std::error_code ec;
    std::string val0 = "00000000";
    std::string val1 = "11111111";
    std::string val2 = "22222222";
    std::string val3 = "33333333";
    std::string val4 = "44444444";
    std::string val5 = "55555555";
    {
        WriteToLogFileWithBackup(log_file.string(), 40, 3, val0);
        EXPECT_TRUE(fs::exists(log_file, ec));
        EXPECT_FALSE(fs::exists(MakeBackupLogName(log_file.string(), 1), ec));
        auto data = tst::ReadFileAsTable(log_file.string());
        ASSERT_TRUE(data.size() == 1);
        auto table = cma::tools::SplitString(data[0], " ");
        ASSERT_TRUE(table.size() == 3);
        EXPECT_TRUE(table[2] == val0);
    }

    {
        WriteToLogFileWithBackup(log_file.string(), 40, 3, val1);
        EXPECT_TRUE(fs::exists(log_file, ec));
        auto log_file_1 = MakeBackupLogName(log_file.string(), 1);
        EXPECT_TRUE(fs::exists(log_file_1, ec));

        auto data = tst::ReadFileAsTable(log_file.string());
        ASSERT_TRUE(data.size() == 1);
        auto table = cma::tools::SplitString(data[0], " ");
        ASSERT_TRUE(table.size() == 3);
        EXPECT_TRUE(table[2] == val1);

        auto data1 = tst::ReadFileAsTable(log_file_1);
        ASSERT_TRUE(data1.size() == 1);
        auto table1 = cma::tools::SplitString(data1[0], " ");
        ASSERT_TRUE(table1.size() == 3);
        EXPECT_TRUE(table1[2] == val0);
    }

    {
        WriteToLogFileWithBackup(log_file.string(), 40, 3, val2);
        WriteToLogFileWithBackup(log_file.string(), 40, 3, val3);  // log.log.2
        WriteToLogFileWithBackup(log_file.string(), 40, 3, val4);  // log.log.1
        WriteToLogFileWithBackup(log_file.string(), 40, 3, val5);  // log.log

        EXPECT_TRUE(FindString(log_file.string(), 3, val2));
        EXPECT_TRUE(FindString(log_file.string(), 2, val3));
        EXPECT_TRUE(FindString(log_file.string(), 1, val4));
        EXPECT_TRUE(FindString(log_file.string(), 0, val5));
    }

    // check for 0
    tst::SafeCleanTempDir();
    {
        WriteToLogFileWithBackup(log_file.string(), 40, 0, val0);
        EXPECT_TRUE(fs::exists(log_file, ec));
        EXPECT_FALSE(fs::exists(MakeBackupLogName(log_file.string(), 1), ec));
        auto data = tst::ReadFileAsTable(log_file.string());
        ASSERT_TRUE(data.size() == 1);
        auto table = cma::tools::SplitString(data[0], " ");
        ASSERT_TRUE(table.size() == 3);
        EXPECT_TRUE(table[2] == val0);
    }

    {
        WriteToLogFileWithBackup(log_file.string(), 40, 0, val1);
        EXPECT_TRUE(fs::exists(log_file, ec));
        EXPECT_FALSE(fs::exists(MakeBackupLogName(log_file.string(), 1), ec));
        auto data = tst::ReadFileAsTable(log_file.string());
        ASSERT_TRUE(data.size() == 1);
        auto table = cma::tools::SplitString(data[0], " ");
        ASSERT_TRUE(table.size() == 3);
        EXPECT_TRUE(table[2] == val1);
    }
}

// TODO(sk): SPlit this test in few
TEST(LogTest, All) {
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());

    // Check Defaults settings on start
    {
        auto &xlogd = XLOG::d;

        auto debug_log_level = cma::cfg::groups::g_global.debugLogLevel();
        if (debug_log_level < 1)
            EXPECT_EQ(xlogd.logParam().directions_,
                      xlog::Directions::kDebuggerPrint);
        else
            EXPECT_EQ(xlogd.logParam().directions_,
                      xlog::Directions::kDebuggerPrint |
                          xlog::Directions::kFilePrint);

        EXPECT_TRUE(xlogd.type() == XLOG::LogType::debug);
    }

    {
        auto &xlogl = XLOG::l;
        EXPECT_EQ(
            xlogl.logParam().directions_,
            xlog::Directions::kDebuggerPrint | xlog::Directions::kFilePrint);
        EXPECT_EQ(xlogl.type(), XLOG::LogType::log);
    }

    {
        auto &xlogt = XLOG::t;
        EXPECT_EQ(xlogt.logParam().directions_,
                  xlog::Directions::kDebuggerPrint);
        EXPECT_EQ(xlogt.type(), XLOG::LogType::trace);
    }

    {
        auto &xlogstdio = XLOG::stdio;
        EXPECT_EQ(xlogstdio.logParam().directions_,
                  xlog::Directions::kStdioPrint);
        EXPECT_EQ(xlogstdio.type(), XLOG::LogType::stdio);
    }

    // DEFAULT
    auto prefix = cma::cfg::GetDefaultPrefixName();
    auto prefix_ascii = wtools::ToUtf8(prefix);
    const auto &lp = l.logParam();

    EXPECT_TRUE(lp.directions_ & xlog::Directions::kDebuggerPrint);
    EXPECT_TRUE(lp.filename()[0] != 0);

    // Check API
    {
        Emitter logger(LogType::log);
        const auto &lp = logger.logParam();
        EXPECT_TRUE(lp.directions_ & xlog::Directions::kFilePrint);
        logger.configFile(cma::cfg::GetCurrentLogFileName());
        EXPECT_TRUE(cma::cfg::GetCurrentLogFileName() == lp.filename());
        logger.configPrefix(prefix);
        EXPECT_TRUE(prefix == lp.prefix());
        EXPECT_TRUE(prefix_ascii == lp.prefixAscii());
    }

    {
        Emitter logger(LogType::debug);
        auto &lp = logger.logParam();
        EXPECT_FALSE(lp.directions_ & xlog::Directions::kFilePrint);
    }

    {
        Emitter logger(LogType::trace);
        auto &lp = logger.logParam();
        EXPECT_FALSE(lp.directions_ & xlog::Directions::kFilePrint);

        logger.enableFileLog(true);
        EXPECT_TRUE(lp.directions_ & xlog::Directions::kFilePrint);

        logger.enableFileLog(false);
        EXPECT_FALSE(lp.directions_ & xlog::Directions::kFilePrint);
    }

    EXPECT_TRUE(lp.directions_ & xlog::Directions::kDebuggerPrint);

    // CLEAN FILE
    {
        Emitter logger(LogType::log);
        auto &lp = logger.logParam();
        logger.configFile("");
        EXPECT_TRUE(lp.filename()[0] == 0) << "File not changed";
        EXPECT_TRUE(lp.directions_ & xlog::Directions::kFilePrint)
            << "Flag was changed";
        EXPECT_TRUE(lp.directions_ & xlog::Directions::kDebuggerPrint)
            << "Flag was changed";

        logger.configPrefix(L"ac");
        std::string new_prefix = lp.prefixAscii();
        EXPECT_TRUE(new_prefix == "ac");
    }

    // DEFAULT CONFIG
    std::string fname = "a";
    setup::ChangeLogFileName(fname);
    EXPECT_EQ(fname, XLOG::l.getLogParam().filename());
    EXPECT_EQ(fname, XLOG::d.getLogParam().filename());
    EXPECT_EQ(fname, XLOG::t.getLogParam().filename());
    EXPECT_TRUE(XLOG::stdio.getLogParam().filename().empty());

    setup::EnableDebugLog(true);
    EXPECT_TRUE(XLOG::d.getLogParam().directions_ &
                xlog::Directions::kFilePrint);
    setup::EnableDebugLog(false);
    EXPECT_FALSE(XLOG::d.getLogParam().directions_ &
                 xlog::Directions::kFilePrint);

    setup::EnableWinDbg(false);
    EXPECT_FALSE(XLOG::l.getLogParam().directions_ &
                 xlog::Directions::kDebuggerPrint);
    EXPECT_FALSE(XLOG::d.getLogParam().directions_ &
                 xlog::Directions::kDebuggerPrint);
    EXPECT_FALSE(XLOG::t.getLogParam().directions_ &
                 xlog::Directions::kDebuggerPrint);
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ &
                 xlog::Directions::kDebuggerPrint);

    setup::EnableWinDbg(true);
    EXPECT_TRUE(XLOG::l.getLogParam().directions_ &
                xlog::Directions::kDebuggerPrint);
    EXPECT_TRUE(XLOG::d.getLogParam().directions_ &
                xlog::Directions::kDebuggerPrint);
    EXPECT_TRUE(XLOG::t.getLogParam().directions_ &
                xlog::Directions::kDebuggerPrint);
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ &
                 xlog::Directions::kDebuggerPrint);

    setup::ReConfigure();
    EXPECT_EQ(XLOG::l.getLogParam().filename(),
              cma::cfg::GetCurrentLogFileName());
    EXPECT_EQ(XLOG::d.getLogParam().filename(),
              cma::cfg::GetCurrentLogFileName());
    EXPECT_EQ(XLOG::t.getLogParam().filename(),
              cma::cfg::GetCurrentLogFileName());
    EXPECT_EQ(XLOG::stdio.getLogParam().filename(), std::string(""));

    EXPECT_TRUE(XLOG::l.getLogParam().directions_ &
                xlog::Directions::kFilePrint);
    EXPECT_TRUE(XLOG::d.getLogParam().directions_ &
                xlog::Directions::kFilePrint)
        << "check debug=yes in cfg";
    EXPECT_FALSE(XLOG::t.getLogParam().directions_ &
                 xlog::Directions::kFilePrint)
        << "check debug=yes in cfg";
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ &
                 xlog::Directions::kFilePrint);

    EXPECT_TRUE(XLOG::l.getLogParam().directions_ &
                xlog::Directions::kDebuggerPrint);
    EXPECT_TRUE(XLOG::d.getLogParam().directions_ &
                xlog::Directions::kDebuggerPrint);
    EXPECT_TRUE(XLOG::t.getLogParam().directions_ &
                xlog::Directions::kDebuggerPrint);
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ &
                 xlog::Directions::kDebuggerPrint);

    EXPECT_FALSE(XLOG::l.getLogParam().directions_ &
                 xlog::Directions::kEventPrint);
    EXPECT_FALSE(XLOG::d.getLogParam().directions_ &
                 xlog::Directions::kEventPrint);
    EXPECT_FALSE(XLOG::t.getLogParam().directions_ &
                 xlog::Directions::kEventPrint);
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ &
                 xlog::Directions::kEventPrint);
}

TEST(LogTest, Simulation) {
    GTEST_SKIP() << "This test is not finished";
    // Output to log
    XLOG::l() << L"This streamed Log Entry and"  // body
                                                 // .....
              << " this is extension 1"          // body
              << '\n';                           // finish
                                                 // Variant two
    XLOG::l() << L"This streamed Log Entry and"  // body
                                                 // .....
              << " this is extension 2"          // body
        ;                                        // finish

    // Variant THREE AND BASIC
    XLOG::l(XLOG::kDrop, "This is dropped a l log {} {}", "x"s, 24);
    if constexpr (false) {
        XLOG::l(XLOG::kBp, "This is breakpoint {} {}", "x"s, 24);
    }

    XLOG::d(XLOG::kForce | XLOG::kFile, "This is a forced d log {} {}", "x"s,
            24);

    // Example of debug tracing. In release this output disappears
    XLOG::d("This is a standard debug out {} {}", "x"s, 24);

    // Example of logging. This output exists in release!
    XLOG::l("This is a standard LOG out {} {}", "x"s, 24);
    XLOG::l() << "This is ALSO a standard LOG out"
              << "x"s << 24;

    XLOG::stdio() << XLOG::d("This is stdio write {} {}", "x"s, 24)
                  << '\n';  // you need this usually to have caret return

    XLOG::stdio("This is stdio write TOO {} {}", "x"s,
                24);  // you need this usually to have caret return
}

TEST(LogTest, EmitterLogRotation) {
    XLOG::Emitter logger(XLOG::LogType::log);
    logger.setLogRotation(3, 1024 * 1024);
    EXPECT_EQ(logger.getBackupLogMaxCount(), 3);
    EXPECT_EQ(logger.getBackupLogMaxSize(), 1024 * 1024);
    logger.setLogRotation(0, 0);
    EXPECT_EQ(logger.getBackupLogMaxCount(), 0);
    EXPECT_EQ(logger.getBackupLogMaxSize(), 256 * 1024);

    logger.setLogRotation(1000, 1024 * 1024 * 1024);
    EXPECT_EQ(logger.getBackupLogMaxCount(), 64);
    EXPECT_EQ(logger.getBackupLogMaxSize(), 256 * 1024 * 1024);
}

TEST(LogTest, Setup) {
    using namespace xlog;
    using namespace XLOG;
    auto a_file = "a.log";
    setup::ChangeLogFileName(a_file);
    auto fname = std::string(l.getLogParam().filename());
    EXPECT_TRUE(fname == a_file);

    setup::EnableDebugLog(true);
    EXPECT_TRUE((d.getLogParam().directions_ & Directions::kFilePrint) != 0);

    fname = std::string(d.getLogParam().filename());
    EXPECT_TRUE(fname == a_file);

    setup::EnableDebugLog(false);
    EXPECT_TRUE((d.getLogParam().directions_ & Directions::kFilePrint) == 0);

    setup::EnableWinDbg(false);
    EXPECT_EQ(l.getLogParam().directions_ & Directions::kDebuggerPrint, 0);
    EXPECT_EQ(d.getLogParam().directions_ & Directions::kDebuggerPrint, 0);
    EXPECT_EQ(t.getLogParam().directions_ & Directions::kDebuggerPrint, 0);

    setup::EnableWinDbg(true);
    EXPECT_TRUE((d.getLogParam().directions_ & Directions::kDebuggerPrint) !=
                0);
}

std::string return_current_time_and_date() {
    auto now = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(now);

    std::stringstream ss;
    ss << std::put_time(std::localtime(&in_time_t), "%Y-%m-%d %X");  // NOLINT
    return ss.str();
}

TEST(LogTest, EventTest) {
    if constexpr (false) {
        // #TODO place in docu
        // #REFERENCE how to use windows event log
        XLOG::details::LogWindowsEventCritical(1, "Test is on {}", "error!");
        XLOG::l(XLOG::kCritError) << "Streamed test output kCritError";
        XLOG::l(XLOG::kEvent) << "Streamed test output kEvent";
    }
}

TEST(LogTest, Functional) {
    namespace fs = std::filesystem;
    std::string log_file_name = "test_file.log";
    fs::path logf = log_file_name;
    fs::remove(logf);

    cma::OnStartTest();
    setup::ChangeLogFileName(wtools::ToUtf8(logf.wstring()));

    XLOG::l("simple test");
    XLOG::l(kCritError)("<GTEST> std test {}", 5);
    XLOG::l(kCritError) << "<GTEST> stream test";

    XLOG::l.t() << " trace";
    XLOG::l.w() << " warn";
    XLOG::l.e() << " error";
    XLOG::l.i() << " info";

    XLOG::l.crit("<GTEST> This is critical ptr is {} code is {}", nullptr, 5);
    XLOG::l("filesystem test {}", fs::path("c:\\a\\a"));
    std::error_code ec;
    EXPECT_TRUE(fs::exists(logf, ec));  // check that file is exists

    {
        std::ifstream in(logf.c_str());
        std::stringstream sstr;
        sstr << in.rdbuf();
        auto contents = sstr.str();
        auto result = cma::tools::SplitString(contents, "\n");
        ASSERT_EQ(result.size(), 9);
        ASSERT_EQ(result.size(), std::ranges::count(contents, '\n'));
        EXPECT_NE(std::string::npos, result[0].find("simple test"));
        EXPECT_NE(std::string::npos, result[1].find("<GTEST> std test"));
        EXPECT_NE(std::string::npos, result[2].find("<GTEST> stream test"));
        EXPECT_NE(std::string::npos, result[2].find("[ERROR:CRITICAL]"));

        constexpr size_t start_position = 32;
        EXPECT_LE(start_position, result[3].find("[Trace]  trace"))
            << "result=" << result[3];
        EXPECT_LE(start_position, result[4].find("[Warn ]  warn"))
            << "result=" << result[4];
        EXPECT_LE(start_position, result[5].find("[Err  ]  error"))
            << "result=" << result[5];
        EXPECT_LE(start_position, result[6].find(" info"));
        EXPECT_LE(
            start_position,
            result[7].find(
                "[ERROR:CRITICAL] <GTEST> This is critical ptr is 0x0 code is 5"));
        EXPECT_LE(start_position,
                  result[8].find("[Err  ] filesystem test c:\\a\\a"));
    }
    fs::remove(logf);
}

namespace details {
TEST(LogTest, Level2Type) {
    EXPECT_EQ(LoggerEventLevelToWindowsEventType(EventLevel::critical),
              EVENTLOG_ERROR_TYPE);
    EXPECT_EQ(LoggerEventLevelToWindowsEventType(EventLevel::error),
              EVENTLOG_ERROR_TYPE);
    EXPECT_EQ(LoggerEventLevelToWindowsEventType(EventLevel::information),
              EVENTLOG_INFORMATION_TYPE);
    EXPECT_EQ(LoggerEventLevelToWindowsEventType(EventLevel::success),
              EVENTLOG_SUCCESS);
    EXPECT_EQ(LoggerEventLevelToWindowsEventType(EventLevel::warning),
              EVENTLOG_WARNING_TYPE);
}
}  // namespace details

}  // namespace XLOG
