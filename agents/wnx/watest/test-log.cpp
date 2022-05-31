// test-log.cpp :

#include "pch.h"

#include <filesystem>
#include <string>

#include "cfg.h"
#include "logger.h"
#include "on_start.h"
#include "read_file.h"
#include "test_tools.h"

namespace xlog {
TEST(xlogTest, xlogLowLevel) {
    EXPECT_TRUE(xlog::IsAddCrFlag(xlog::kAddCr));
    EXPECT_FALSE(xlog::IsAddCrFlag(~xlog::kAddCr));

    EXPECT_TRUE(xlog::IsNoCrFlag(xlog::kNoCr));
    EXPECT_FALSE(xlog::IsNoCrFlag(~xlog::kNoCr));

    std::string s;
    EXPECT_NO_THROW(xlog::RmCr(s));
    xlog::AddCr(s);
    EXPECT_EQ(s, "\n");
    xlog::AddCr(s);
    EXPECT_EQ(s, "\n");
    xlog::RmCr(s);
    EXPECT_EQ(s, "");
    EXPECT_NO_THROW(xlog::RmCr(s));
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
    xlog::LogParam lp{0};
    constexpr int mark = 0x1000'0000;
    lp.directions_ = mark;

    EXPECT_EQ(Mods2Directions(lp, Mods::kFile), mark | xlog::kFilePrint);
    EXPECT_EQ(Mods2Directions(lp, Mods::kStdio), mark | xlog::kStdioPrint);
    EXPECT_EQ(Mods2Directions(lp, Mods::kEvent), mark | xlog::kEventPrint);

    constexpr int all_mark = 0xFFFF'FFFF;
    lp.directions_ = all_mark;

    EXPECT_EQ(Mods2Directions(lp, Mods::kNoFile), all_mark & ~xlog::kFilePrint);
    EXPECT_EQ(Mods2Directions(lp, Mods::kNoStdio),
              all_mark & ~xlog::kStdioPrint);
    EXPECT_EQ(Mods2Directions(lp, Mods::kNoEvent),
              all_mark & ~xlog::kEventPrint);
}
}  // namespace internal

TEST(LogTest, RotationFileNameCreation) {
    EXPECT_NO_THROW(details::MakeBackupLogName("a", 0));
    EXPECT_EQ("a", details::MakeBackupLogName("a", 0));
    EXPECT_EQ("a.2", details::MakeBackupLogName("a", 2));
    EXPECT_EQ("a.5", details::MakeBackupLogName("a", 5));
}

TEST(LogTest, RotationFileCfgParam) {
    for (auto t : {XLOG::LogType::debug, XLOG::LogType::log,
                   XLOG::LogType::stdio, XLOG::LogType::trace}) {
        XLOG::Emitter e(t);
        auto max_count = e.getBackupLogMaxCount();
        auto max_size = e.getBackupLogMaxSize();
        EXPECT_TRUE(max_count < 32);
        EXPECT_TRUE(max_size > 100'000);
        EXPECT_TRUE(max_size < 1'000'000'000);
    }
}

static bool FindString(const std::string &name, unsigned int index,
                       const std::string &Text) {
    auto filename = details::MakeBackupLogName(name, index);
    auto data = tst::ReadFileAsTable(filename);
    if (data.size() != 1) return false;
    auto table = cma::tools::SplitString(data[0], " ");
    if (table.size() != 3) return false;
    return table[2] == Text;
}

TEST(LogTest, RotationFile) {
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());

    namespace fs = std::filesystem;
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

TEST(LogTest, All) {
    auto temp_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_fs->loadFactoryConfig());
    // tests of log:
    // stream OUT
    // e
    using namespace cma::cfg;
    using namespace std;

    // Check Defaults settings on start
    {
        auto &xlogd = XLOG::d;

        auto debug_log_level = cma::cfg::groups::global.debugLogLevel();
        if (debug_log_level < 1)
            EXPECT_TRUE(xlogd.log_param_.directions_ ==
                        xlog::Directions::kDebuggerPrint);
        else
            EXPECT_TRUE(xlogd.log_param_.directions_ ==
                        (xlog::Directions::kDebuggerPrint |
                         xlog::Directions::kFilePrint));

        EXPECT_TRUE(xlogd.type_ == XLOG::LogType::debug);
    }

    {
        auto &xlogl = XLOG::l;
        EXPECT_TRUE(
            xlogl.log_param_.directions_ ==
            (xlog::Directions::kDebuggerPrint | xlog::Directions::kFilePrint));
        EXPECT_TRUE(xlogl.type_ == XLOG::LogType::log);
    }

    {
        auto &xlogt = XLOG::t;
        EXPECT_TRUE(xlogt.log_param_.directions_ ==
                    (xlog::Directions::kDebuggerPrint));
        EXPECT_TRUE(xlogt.type_ == XLOG::LogType::trace);
    }

    {
        auto &xlogstdio = XLOG::stdio;
        EXPECT_TRUE(xlogstdio.log_param_.directions_ ==
                    xlog::Directions::kStdioPrint);
        EXPECT_TRUE(xlogstdio.type_ == XLOG::LogType::stdio);
    }

    // DEFAULT
    auto prefix = GetDefaultPrefixName();
    auto prefix_ascii = wtools::ToUtf8(prefix);
    auto &lp = l.log_param_;

    EXPECT_TRUE(lp.directions_ & xlog::Directions::kDebuggerPrint);
    EXPECT_TRUE(lp.filename()[0] != 0);

    // Check API
    {
        XLOG::Emitter l(XLOG::LogType::log);
        auto &lp = l.log_param_;
        EXPECT_TRUE(lp.directions_ & xlog::Directions::kFilePrint);
        l.configFile(GetCurrentLogFileName());
        EXPECT_TRUE(GetCurrentLogFileName() == lp.filename());
        l.configPrefix(prefix);
        EXPECT_TRUE(prefix == lp.prefix());
        EXPECT_TRUE(prefix_ascii == lp.prefixAscii());
    }

    {
        XLOG::Emitter d(XLOG::LogType::debug);
        auto &lp = t.log_param_;
        EXPECT_FALSE(lp.directions_ & xlog::Directions::kFilePrint);
    }

    {
        XLOG::Emitter t(XLOG::LogType::trace);
        auto &lp = t.log_param_;
        EXPECT_FALSE(lp.directions_ & xlog::Directions::kFilePrint);

        t.enableFileLog(true);
        EXPECT_TRUE(lp.directions_ & xlog::Directions::kFilePrint);

        t.enableFileLog(false);
        EXPECT_FALSE(lp.directions_ & xlog::Directions::kFilePrint);
    }

    EXPECT_TRUE(lp.directions_ & xlog::Directions::kDebuggerPrint);

    // CLEAN FILE
    {
        XLOG::Emitter l(XLOG::LogType::log);
        auto &lp = l.log_param_;
        l.configFile("");
        EXPECT_TRUE(lp.filename()[0] == 0) << "File not changed";
        EXPECT_TRUE(lp.directions_ & xlog::Directions::kFilePrint)
            << "Flag was changed";
        EXPECT_TRUE(lp.directions_ & xlog::Directions::kDebuggerPrint)
            << "Flag was changed";

        l.configPrefix(L"ac");
        std::string new_prefix = lp.prefixAscii();
        EXPECT_TRUE(new_prefix == "ac");
    }

    // *************************************************************
    // *************************************************************
    // *************************************************************
    // *************************************************************

    // DEFAULT CONFIG
    std::string fname = "a";
    setup::ChangeLogFileName(fname);
    EXPECT_EQ(fname, XLOG::l.getLogParam().filename());
    EXPECT_EQ(fname, XLOG::d.getLogParam().filename());
    EXPECT_EQ(fname, XLOG::t.getLogParam().filename());
    EXPECT_EQ(std::string(""), XLOG::stdio.getLogParam().filename());

    setup::EnableDebugLog(true);
    EXPECT_TRUE(XLOG::d.getLogParam().directions_ & xlog::kFilePrint);
    setup::EnableDebugLog(false);
    EXPECT_FALSE(XLOG::d.getLogParam().directions_ & xlog::kFilePrint);

    setup::EnableWinDbg(false);
    EXPECT_FALSE(XLOG::l.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_FALSE(XLOG::d.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_FALSE(XLOG::t.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ & xlog::kDebuggerPrint);

    setup::EnableWinDbg(true);
    EXPECT_TRUE(XLOG::l.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_TRUE(XLOG::d.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_TRUE(XLOG::t.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ & xlog::kDebuggerPrint);

    setup::ReConfigure();
    EXPECT_EQ(XLOG::l.getLogParam().filename(), GetCurrentLogFileName());
    EXPECT_EQ(XLOG::d.getLogParam().filename(), GetCurrentLogFileName());
    EXPECT_EQ(XLOG::t.getLogParam().filename(), GetCurrentLogFileName());
    EXPECT_EQ(XLOG::stdio.getLogParam().filename(), std::string(""));

    EXPECT_TRUE(XLOG::l.getLogParam().directions_ & xlog::kFilePrint);
    EXPECT_TRUE(XLOG::d.getLogParam().directions_ & xlog::kFilePrint)
        << "check debug=yes in cfg";
    EXPECT_FALSE(XLOG::t.getLogParam().directions_ & xlog::kFilePrint)
        << "check debug=yes in cfg";
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ & xlog::kFilePrint);

    EXPECT_TRUE(XLOG::l.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_TRUE(XLOG::d.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_TRUE(XLOG::t.getLogParam().directions_ & xlog::kDebuggerPrint);
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ & xlog::kDebuggerPrint);

    EXPECT_FALSE(XLOG::l.getLogParam().directions_ & xlog::kEventPrint);
    EXPECT_FALSE(XLOG::d.getLogParam().directions_ & xlog::kEventPrint);
    EXPECT_FALSE(XLOG::t.getLogParam().directions_ & xlog::kEventPrint);
    EXPECT_FALSE(XLOG::stdio.getLogParam().directions_ & xlog::kEventPrint);

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
    XLOG::l(XLOG::kDrop, "This is dropped a l log {} {}", string("x"), 24);
    if (0) {
        XLOG::l(XLOG::kBp, "This is breakpoint {} {}", string("x"), 24);
    }

    XLOG::d(XLOG::kForce | XLOG::kFile, "This is a forced d log {} {}",
            std::string("x"), 24);

    // Example of debug tracing. In release this output disappears
    XLOG::d("This is a standard debug out {} {}", string("x"), 24);

    // Example of logging. This output exists in release!
    XLOG::l("This is a standard LOG out {} {}", string("x"), 24);
    XLOG::l() << "This is ALSO a standard LOG out" << string(" x ") << 24;

    XLOG::stdio() << XLOG::d("This is stdio write {} {}", string("x"), 24)
                  << '\n';  // you need this usually to have caret return

    XLOG::stdio("This is stdio write TOO {} {}", string("x"),
                24);  // you need this usually to have caret return

    // *************************************************************
    // *************************************************************
    // *************************************************************
    // *************************************************************
}

TEST(LogTest, EmitterLogRotation) {
    XLOG::Emitter l(XLOG::LogType::log);
    l.setLogRotation(3, 1024 * 1024);
    EXPECT_EQ(l.getBackupLogMaxCount(), 3);
    EXPECT_EQ(l.getBackupLogMaxSize(), 1024 * 1024);
    l.setLogRotation(0, 0);
    EXPECT_EQ(l.getBackupLogMaxCount(), 0);
    EXPECT_EQ(l.getBackupLogMaxSize(), 256 * 1024);

    l.setLogRotation(1000, 1024 * 1024 * 1024);
    EXPECT_EQ(l.getBackupLogMaxCount(), 64);
    EXPECT_EQ(l.getBackupLogMaxSize(), 256 * 1024 * 1024);
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
    ss << std::put_time(std::localtime(&in_time_t), "%Y-%m-%d %X");
    return ss.str();
}

TEST(LogTest, EventTest) {
    if (false) {
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

    cma::OnStart(cma::AppType::test);
    setup::ChangeLogFileName(logf.u8string());

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
        auto n = std::count(contents.begin(), contents.end(), '\n');
        auto result = cma::tools::SplitString(contents, "\n");
        ASSERT_EQ(result.size(), 9);
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

// Do formatting:
namespace fmt {
TEST(LogTest, Fmt) {
    auto result = formatv("-{} {}-", 3, "c");
    EXPECT_EQ(result, "-3 c-");

    EXPECT_NO_THROW(formatv("<GTEST> -{} {}-", 3));
}
}  // namespace fmt
