// test-section-logwatch.cpp

//
#include "pch.h"

#include <filesystem>

#include "cfg.h"
#include "cfg_engine.h"
#include "common/wtools.h"
#include "providers/logwatch_event.h"
#include "providers/logwatch_event_details.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

using cma::evl::SkipDuplicatedRecords;
using std::chrono::steady_clock;
namespace fs = std::filesystem;

namespace cma::provider {

static void LoadTestConfig(YAML::Node node) {
    node["logwatch"] = YAML::Load(
        "  enabled : yes\n"
        "  sendall : no\n"
        "  vista_api: no\n"
        "  skip_duplicated: no\n"
        "  logfile :\n"
        "    - 'Application': crit context\n"
        "    - 'System' : warn nocontext\n"
        "    - 'Demo' : all nocontext\n"
        "    - '': off nocontext\n"
        "    - '*' : warn context\n");
}

static void LoadTestConfigAll(YAML::Node node) {
    node["logwatch"] = YAML::Load(
        "  enabled : yes\n"
        "  sendall : yes\n"
        "  vista_api: yes\n"
        "  skip_duplicated: no\n"
        "  max_size: 11\n"
        "  max_line_length: 22\n"
        "  max_entries: 33\n"
        "  timeout: 44\n");
}

constexpr int LogWatchSections_Main = 3;
constexpr int LogWatchSections_Test = 5;

TEST(LogWatchEventTest, Consts) {
    EXPECT_EQ(cfg::EventLevels::kOff, LabelToEventLevel({}));
    EXPECT_EQ(cfg::EventLevels::kOff, LabelToEventLevel(""));
    EXPECT_EQ(cfg::EventLevels::kOff, LabelToEventLevel("off"));
    EXPECT_EQ(cfg::EventLevels::kOff, LabelToEventLevel("oFf"));
    EXPECT_EQ(cfg::EventLevels::kIgnore, LabelToEventLevel("ignoRe"));
    EXPECT_EQ(cfg::EventLevels::kIgnore, LabelToEventLevel("ignore"));
    EXPECT_EQ(cfg::EventLevels::kWarn, LabelToEventLevel("warn"));
    EXPECT_EQ(cfg::EventLevels::kCrit, LabelToEventLevel("crit"));
    EXPECT_EQ(cfg::EventLevels::kAll, LabelToEventLevel("all"));
    EXPECT_EQ(cfg::EventLevels::kAll, LabelToEventLevel("alL"));
    EXPECT_EQ(cfg::EventLevels::kOff, LabelToEventLevel("all "));
}

TEST(LogWatchEventTest, GetLastPos) {
    {
        auto p = GetLastPos(EvlType::classic, "Application");
        ASSERT_TRUE(p.has_value());
        EXPECT_TRUE(*p > 0);
    }

    {
        auto p = GetLastPos(EvlType::classic, "State<GTEST>");
        EXPECT_FALSE(p.has_value());
    }
}

/// \brief Keeps temporary folder and pair of file names and dirs
class LogWatchEventFixture : public ::testing::Test {
public:
    cma::evl::EventLogDebug event_log{tst::SimpleLogData()};
    State state{"Application", cfg::kFromBegin, true};
    const size_t max_pos{tst::SimpleLogData().size()};
    static constexpr LogWatchLimits lwl_all_with_skip{
        .max_size = 10'000,
        .max_line_length = -1,
        .max_entries = -1,
        .timeout = -1,
        .skip = SkipDuplicatedRecords::yes};
    static constexpr LogWatchLimits lwl_all_without_skip{
        .max_size = 10'000,
        .max_line_length = -1,
        .max_entries = -1,
        .timeout = -1,
        .skip = SkipDuplicatedRecords::no};
    static constexpr LogWatchLimits lwl_all_with_skip_and_cut_same{
        .max_size = 10'000,
        .max_line_length = -1,
        .max_entries = 2,
        .timeout = -1,
        .skip = SkipDuplicatedRecords::yes};
    static constexpr LogWatchLimits lwl_all_with_skip_and_cut_diff{
        .max_size = 10'000,
        .max_line_length = -1,
        .max_entries = 4,
        .timeout = -1,
        .skip = SkipDuplicatedRecords::yes};
};

TEST_F(LogWatchEventFixture, DumpEventLogWithSkip) {
    auto [pos, out] = DumpEventLog(event_log, state, lwl_all_with_skip);
    EXPECT_EQ(pos, max_pos - 1);
    auto table = tools::SplitString(out, "\n");
    EXPECT_EQ(table.size(), 5);  // 3 unique entry + 2 repeated messages
    EXPECT_EQ(fmt::format(evl::kSkippedMessageFormat, 1), table[1] + "\n");
    EXPECT_EQ(fmt::format(evl::kSkippedMessageFormat, 2), table[4] + "\n");
    for (const auto &x : {0, 2, 3}) {
        EXPECT_NE(table[x].find("Message "), std::string::npos);
    }
}

TEST_F(LogWatchEventFixture, DumpEventLogWithoutSkip) {
    auto [pos, out] = DumpEventLog(event_log, state, lwl_all_without_skip);
    EXPECT_EQ(pos, max_pos - 1);
    auto table = tools::SplitString(out, "\n");
    EXPECT_EQ(table.size(), max_pos);
    for (const auto &x : table) {
        EXPECT_NE(x.find("Message "), std::string::npos);
    }
}

TEST_F(LogWatchEventFixture, DumpEventLogWithSkipAndCutOnSameEntry) {
    // special case when cut occurs at the repeating entry
    // we can cut  at the entries+1 !
    auto lwl = lwl_all_with_skip_and_cut_same;
    auto [pos, out] = DumpEventLog(event_log, state, lwl);
    EXPECT_EQ(pos, lwl.max_entries);
    auto table = tools::SplitString(out, "\n");
    EXPECT_EQ(table.size(), lwl.max_entries + 1);
    EXPECT_EQ(fmt::format(evl::kSkippedMessageFormat, 1), table[1] + "\n");
    EXPECT_NE(table[0].find("Message "), std::string::npos);
}

TEST_F(LogWatchEventFixture, DumpEventLogWithSkipAndCutOnDiffEntry) {
    auto lwl = lwl_all_with_skip_and_cut_diff;
    auto [pos, out] = DumpEventLog(event_log, state, lwl);
    EXPECT_EQ(pos, lwl.max_entries - 1);
    auto table = tools::SplitString(out, "\n");
    EXPECT_EQ(table.size(), lwl.max_entries);
    EXPECT_EQ(fmt::format(evl::kSkippedMessageFormat, 1), table[1] + "\n");
    EXPECT_NE(table[0].find("Message "), std::string::npos);
}

TEST(LogWatchEventTest, DumpEventLog) {
    auto ptr = cma::evl::OpenEvl(L"Application", false);
    ASSERT_TRUE(ptr);

    State state("Application", 0, true);
    {
        LogWatchLimits lwl{.max_size = 10'000,
                           .max_line_length = -1,
                           .max_entries = -1,
                           .timeout = -1,
                           .skip = SkipDuplicatedRecords::no};
        auto [pos, out] = DumpEventLog(*ptr, state, lwl);
        EXPECT_TRUE(pos > 0);
        EXPECT_TRUE(out.length() < 12'000);
    }

    {
        LogWatchLimits lwl{.max_size = -1,
                           .max_line_length = 10,
                           .max_entries = 19,
                           .timeout = -1,
                           .skip = SkipDuplicatedRecords::no};
        auto [pos, out] = DumpEventLog(*ptr, state, lwl);
        EXPECT_TRUE(pos > 0);
        EXPECT_TRUE(out.length() < 20000);
        auto table = cma::tools::SplitString(out, "\n");
        ASSERT_EQ(table.size(), 19);
        for (auto &t : table) EXPECT_TRUE(t.size() <= 10);
    }

    {
        LogWatchLimits lwl{.max_size = -1,
                           .max_line_length = 10,
                           .max_entries = -1,
                           .timeout = -1,
                           .skip = SkipDuplicatedRecords::no};
        auto start = steady_clock::now();
        auto [pos, out] = DumpEventLog(*ptr, state, lwl);
        auto end = steady_clock::now();
        EXPECT_TRUE(
            std::chrono::duration_cast<std::chrono::seconds>(end - start)
                .count() < 2);
    }
}

// check how good can we find objects in entries
TEST(LogWatchEventTest, LoadFromConfig) {
    State state("xx", 1, true);

    LogWatchEntryVector entries;
    EXPECT_FALSE(LoadFromConfig(state, entries));

    LogWatchEntry lwe;

    // make good entry to test
    lwe.loadFrom("XX: warn context");
    entries.push_back(LogWatchEntry(lwe));

    EXPECT_TRUE(LoadFromConfig(state, entries));
    EXPECT_EQ(state.level_, cfg::EventLevels::kWarn);
    EXPECT_TRUE(state.in_config_);
    EXPECT_FALSE(state.hide_context_);
    EXPECT_TRUE(state.presented_);
}

TEST(LogWatchEventTest, LoadFrom) {
    {
        LogWatchEntry lwe;
        lwe.loadFrom("  Abc :   ccc context ddd ");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), cfg::EventLevels::kOff);
        EXPECT_EQ(lwe.name(), "Abc");
        EXPECT_EQ(lwe.context(), true);
    }

    {
        LogWatchEntry lwe;
        lwe.loadFrom("  Abc :   warn ncontext ddd ");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), cfg::EventLevels::kWarn);
        EXPECT_EQ(lwe.name(), "Abc");
        EXPECT_EQ(lwe.context(), false);
    }

    {
        LogWatchEntry lwe;
        lwe.loadFrom("Abc:all context");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), cfg::EventLevels::kAll);
        EXPECT_EQ(lwe.name(), "Abc");
        EXPECT_EQ(lwe.context(), true);
    }

    {
        LogWatchEntry lwe;
        lwe.loadFrom("A :");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), cfg::EventLevels::kOff);
        EXPECT_EQ(lwe.name(), "A");
        EXPECT_EQ(lwe.context(), false);
    }
    {
        LogWatchEntry lwe;
        lwe.loadFrom(R"("":aaa)");
        EXPECT_FALSE(lwe.loaded());
        lwe.loadFrom(R"("    ":aaa)");
        EXPECT_FALSE(lwe.loaded());
        lwe.loadFrom("'  \t\t ':aaa");
        EXPECT_FALSE(lwe.loaded());
    }
    {
        LogWatchEntry lwe;
        lwe.loadFrom(R"("*" : crit nocontext )");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), cfg::EventLevels::kCrit);
        EXPECT_EQ(lwe.name(), "*");
        EXPECT_EQ(lwe.context(), false);
    }
    {
        LogWatchEntry lwe;
        lwe.loadFrom(R"(' *  ' : crit nocontext )");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), cfg::EventLevels::kCrit);
        EXPECT_EQ(lwe.name(), "*");
        EXPECT_EQ(lwe.context(), false);
    }
}

TEST(LogWatchEventTest, CheckFabricConfig) {
    auto test_fs{tst::TempCfgFs::Create()};
    ASSERT_TRUE(test_fs->loadConfig(tst::GetFabricYml()));

    EXPECT_TRUE(
        cfg::GetVal(cfg::groups::kLogWatchEvent, cfg::vars::kEnabled, false));
    EXPECT_FALSE(cfg::GetVal(cfg::groups::kLogWatchEvent,
                             cfg::vars::kLogWatchEventVistaApi, true));
    EXPECT_FALSE(cfg::GetVal(cfg::groups::kLogWatchEvent,
                             cfg::vars::kLogWatchEventSendall, true));
    EXPECT_FALSE(cfg::GetVal(cfg::groups::kLogWatchEvent,
                             cfg::vars::kLogWatchEventSkip, true));

    auto max_size = cfg::GetVal(cfg::groups::kLogWatchEvent,
                                cfg::vars::kLogWatchEventMaxSize, 13);
    EXPECT_EQ(max_size, cfg::logwatch::kMaxSize);

    auto max_line_length =
        cfg::GetVal(cfg::groups::kLogWatchEvent,
                    cfg::vars::kLogWatchEventMaxLineLength, 444);
    EXPECT_EQ(max_line_length, -1);

    auto tout = cfg::GetVal(cfg::groups::kLogWatchEvent,
                            cfg::vars::kLogWatchEventTimeout, 440);
    EXPECT_EQ(tout, -1);

    auto max_entries = cfg::GetVal(cfg::groups::kLogWatchEvent,
                                   cfg::vars::kLogWatchEventTimeout, 445);
    EXPECT_EQ(max_entries, -1);

    auto sections = cfg::GetNode(cfg::groups::kLogWatchEvent,
                                 cfg::vars::kLogWatchEventLogFile);
    ASSERT_TRUE(sections.IsSequence());
    ASSERT_EQ(sections.size(), LogWatchSections_Main);

    // data to be tested against
    const RawLogWatchData base[LogWatchSections_Test] = {
        //{false, "", cfg::EventLevels::kOff, false},
        {true, "Parameters", cfg::EventLevels::kIgnore, false},
        {true, "State", cfg::EventLevels::kIgnore, false},
        {true, "*", cfg::EventLevels::kWarn, false},
    };

    int pos = 0;
    for (const auto &sec : sections) {
        auto type = sec.Type();
        if (!sec.IsMap()) continue;
        YAML::Emitter emit;
        emit << sec;
        LogWatchEntry lwe;
        lwe.loadFrom(emit.c_str());
        EXPECT_EQ(lwe.loaded(), base[pos].loaded_);
        EXPECT_EQ(lwe.level(), base[pos].level_);
        EXPECT_EQ(lwe.name(), base[pos].name_);
        EXPECT_EQ(lwe.context(), base[pos].context_);
        pos++;
    }
    EXPECT_EQ(pos, 3);
}

TEST(LogWatchEventTest, CheckTestConfig) {
    auto test_fs{tst::TempCfgFs::CreateNoIo()};
    auto cfg = cfg::GetLoadedConfig();
    LoadTestConfig(cfg);
    EXPECT_TRUE(
        cfg::GetVal(cfg::groups::kLogWatchEvent, cfg::vars::kEnabled, false));
    EXPECT_FALSE(cfg::GetVal(cfg::groups::kLogWatchEvent,
                             cfg::vars::kLogWatchEventVistaApi, true));
    EXPECT_FALSE(cfg::GetVal(cfg::groups::kLogWatchEvent,
                             cfg::vars::kLogWatchEventSendall, true));
    EXPECT_FALSE(cfg::GetVal(cfg::groups::kLogWatchEvent,
                             cfg::vars::kLogWatchEventSkip, true));

    auto sections = cfg::GetNode(cfg::groups::kLogWatchEvent,
                                 cfg::vars::kLogWatchEventLogFile);
    ASSERT_TRUE(sections.IsSequence());
    ASSERT_EQ(sections.size(), LogWatchSections_Test);

    // data to be tested against
    const RawLogWatchData base[LogWatchSections_Test] = {
        {true, "Application", cfg::EventLevels::kCrit, true},
        {true, "System", cfg::EventLevels::kWarn, false},
        {true, "Demo", cfg::EventLevels::kAll, false},
        {false, "", cfg::EventLevels::kOff, false},
        {true, "*", cfg::EventLevels::kWarn, true},
    };

    int pos = 0;
    for (const auto &sec : sections) {
        auto type = sec.Type();
        if (!sec.IsMap()) continue;
        YAML::Emitter emit;
        emit << sec;
        LogWatchEntry lwe;
        lwe.loadFrom(emit.c_str());
        EXPECT_EQ(lwe.loaded(), base[pos].loaded_);
        EXPECT_EQ(lwe.level(), base[pos].level_);
        EXPECT_EQ(lwe.name(), base[pos].name_);
        EXPECT_EQ(lwe.context(), base[pos].context_);
        pos++;
    }
    EXPECT_EQ(pos, 5);
}

TEST(LogWatchEventTest, MakeStateFileName) {
    EXPECT_TRUE(MakeStateFileName("", "", "").empty());
    EXPECT_TRUE(MakeStateFileName("", ".a", "").empty());
    EXPECT_EQ(MakeStateFileName("a", ".b", ""), "a.b");
    EXPECT_EQ(MakeStateFileName("a", ".b", "1:2"), "a_1_2.b");
    EXPECT_EQ(MakeStateFileName("a", ".b", "1::2:"), "a_1__2_.b");
}

TEST(LogWatchEventTest, ConfigStruct) {
    {
        provider::LogWatchEntry lwe;
        EXPECT_EQ(lwe.name(), "");
        EXPECT_TRUE(lwe.level() == cfg::EventLevels::kOff);
        EXPECT_EQ(lwe.context(), false);
        EXPECT_EQ(lwe.loaded(), false);

        lwe.init("Name", "WARN", true);
        EXPECT_EQ(lwe.name(), "Name");
        EXPECT_TRUE(lwe.level() == cfg::EventLevels::kWarn);
        EXPECT_EQ(lwe.context(), true);
        EXPECT_EQ(lwe.loaded(), true);
    }
    {
        provider::LogWatchEntry lwe;
        lwe.init("Name", "off", true);
        EXPECT_TRUE(lwe.level() == cfg::EventLevels::kOff);
    }

    {
        provider::LogWatchEntry lwe;
        lwe.init("Name", "ignore", true);
        EXPECT_TRUE(lwe.level() == cfg::EventLevels::kIgnore);
    }

    {
        provider::LogWatchEntry lwe;
        lwe.init("Name", "warn", false);
        EXPECT_TRUE(lwe.level() == cfg::EventLevels::kWarn);
        EXPECT_FALSE(lwe.context());
    }
    {
        provider::LogWatchEntry lwe;
        lwe.init("Name", "crit", true);
        EXPECT_TRUE(lwe.level() == cfg::EventLevels::kCrit);
    }
    {
        provider::LogWatchEntry lwe;
        lwe.init("Name", "all", true);
        EXPECT_TRUE(lwe.level() == cfg::EventLevels::kAll);
    }
}

TEST(LogWatchEventTest, ConfigLoadAll) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    LoadTestConfigAll(cfg::GetLoadedConfig());

    LogWatchEvent lw;
    lw.loadConfig();
    EXPECT_EQ(lw.evlType(), EvlType::vista);
    EXPECT_TRUE(lw.sendAll());
    auto lwl = lw.getLogWatchLimits();
    EXPECT_EQ(lwl.max_size, 11);
    EXPECT_EQ(lwl.max_line_length, 22);
    EXPECT_EQ(lwl.max_entries, 33);
    EXPECT_EQ(lwl.timeout, 44);
}

TEST(LogWatchEventTest, LogWatchDefault) {
    LogWatchEvent lw;
    EXPECT_EQ(lw.evlType(), EvlType::classic);
    EXPECT_FALSE(lw.sendAll());
    auto lwl = lw.getLogWatchLimits();
    EXPECT_EQ(lwl.max_entries, cfg::logwatch::kMaxEntries);
    EXPECT_EQ(lwl.max_line_length, cfg::logwatch::kMaxLineLength);
    EXPECT_EQ(lwl.max_size, cfg::logwatch::kMaxSize);
    EXPECT_EQ(lwl.timeout, cfg::logwatch::kTimeout);
}

TEST(LogWatchEventTest, ConfigLoad) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    LoadTestConfig(cfg::GetLoadedConfig());

    LogWatchEvent lw;
    lw.loadConfig();
    auto lwl = lw.getLogWatchLimits();
    EXPECT_EQ(lwl.max_entries, cfg::logwatch::kMaxEntries);
    EXPECT_EQ(lwl.max_line_length, cfg::logwatch::kMaxLineLength);
    EXPECT_EQ(lwl.max_size, cfg::logwatch::kMaxSize);
    EXPECT_EQ(lwl.timeout, cfg::logwatch::kTimeout);
    auto e = lw.entries();
    ASSERT_TRUE(e.size() > 2);
    EXPECT_TRUE(e[0].loaded());
    EXPECT_TRUE(e[1].loaded());
    EXPECT_TRUE(e[0].context() == true);
    EXPECT_TRUE(e[1].context() == false);
    EXPECT_EQ(e[0].name(), "Application");
    EXPECT_EQ(e[1].name(), "System");
    EXPECT_EQ(e[2].name(), "Demo");

    EXPECT_EQ(e[0].level(), cfg::EventLevels::kCrit);
    EXPECT_EQ(e[1].level(), cfg::EventLevels::kWarn);
    EXPECT_EQ(e[2].level(), cfg::EventLevels::kAll);
}

TEST(LogWatchEventTest, ParseStateLine) {
    {
        auto state = details::ParseStateLine("abc|123");
        EXPECT_EQ(state.name_, "abc");
        EXPECT_EQ(state.presented_, false);
        EXPECT_EQ(state.pos_, 123);
    }
    {
        auto state = details::ParseStateLine(" abc |123");
        EXPECT_EQ(state.name_, " abc ");
        EXPECT_EQ(state.presented_, false);
        EXPECT_EQ(state.pos_, 123);
    }
    {
        auto state = details::ParseStateLine("abc123");
        EXPECT_EQ(state.name_, "");
        EXPECT_EQ(state.presented_, false);
        EXPECT_EQ(state.pos_, 0);
    }
    {
        auto state = details::ParseStateLine("abc|123|");
        EXPECT_EQ(state.name_, "abc");
        EXPECT_EQ(state.presented_, false);
        EXPECT_EQ(state.pos_, 123);
    }
    {
        auto state = details::ParseStateLine("abc123|");
        EXPECT_EQ(state.name_, "");
        EXPECT_EQ(state.presented_, false);
        EXPECT_EQ(state.pos_, 0);
    }
    {
        auto state = details::ParseStateLine("|abc123");
        EXPECT_EQ(state.name_, "");
        EXPECT_EQ(state.presented_, false);
        EXPECT_EQ(state.pos_, 0);
    }
    {
        auto state = details::ParseStateLine(" abc |123\n");
        EXPECT_EQ(state.name_, " abc ");
        EXPECT_EQ(state.presented_, false);
        EXPECT_EQ(state.pos_, 123);
    }
}

#define TEST_FILE "test_file.tmp"
TEST(LogWatchEventTest, TestStateFileLoad) {
    fs::path p(TEST_FILE);
    std::ofstream f;
    f.open(p.u8string(), std::ios::trunc | std::ios::binary);
    // array from real life, but not sorted
    auto str =
        "IntelAudioServiceLog|0\n"
        "Application|396747\n"
        "Dell|90\n"
        "HardwareEvents|0\n"
        "Internet Explorer|0\n"
        "Key Management Service|0\n"
        "Security|104159\n"
        "System|21934\n"
        "Windows PowerShell|22012\n"
        "Windows Azure|0\n";
    f.write(str, strlen(str));
    f.close();

    PathVector filelist;
    filelist.push_back(TEST_FILE);

    {
        auto states = details::LoadEventlogOffsets(filelist, false);
        ASSERT_EQ(states.size(), 10);
        EXPECT_EQ(states[0].name_, "Application");
        EXPECT_EQ(states[9].name_, "Windows PowerShell");
        EXPECT_EQ(states[0].pos_, 396747);
        EXPECT_EQ(states[9].pos_, 22012);
        for (auto &s : states) {
            EXPECT_FALSE(s.presented_);
            EXPECT_FALSE(s.name_.empty());
        }
    }

    {
        auto states = details::LoadEventlogOffsets(filelist, true);
        ASSERT_EQ(states.size(), 10);
        for (auto &s : states) {
            EXPECT_TRUE(s.pos_ == 0)
                << "with sendall in true we have reset pos to 0!";
        }
    }
    fs::remove(p);

    {
        PathVector statefiles_bad;
        filelist.push_back(TEST_FILE);
        auto states = details::LoadEventlogOffsets(statefiles_bad,
                                                   false);  // offsets stored
        EXPECT_EQ(states.size(), 0);
    }
}

TEST(LogWatchEventTest, TestAddLog) {
    StateVector states;
    AddLogState(states, false, "xxx", SendMode::normal);
    {
        auto &s0 = states[0];

        EXPECT_EQ(s0.hide_context_, true);              // default
        EXPECT_EQ(s0.level_, cfg::EventLevels::kCrit);  // default
        EXPECT_EQ(s0.pos_, cfg::kFromBegin);            // 4 parameter
        EXPECT_EQ(s0.name_, std::string("xxx"));        // 3 param
        EXPECT_EQ(s0.in_config_, false);                // 2 param
        EXPECT_EQ(s0.presented_, true);                 // default

        s0.presented_ = false;
        AddLogState(states, false, "xxx", SendMode::normal);
        EXPECT_EQ(s0.presented_, true);  // reset for found

        AddLogState(states, true, "xxx", SendMode::normal);
        EXPECT_EQ(s0.in_config_, true);  // reset with 2 param
    }

    {
        AddLogState(states, true, "yyy", SendMode::all);
        auto &s1 = states[1];
        EXPECT_EQ(s1.pos_, 0);                    // 4 parameter
        EXPECT_EQ(s1.name_, std::string("yyy"));  // 3 param
        EXPECT_EQ(s1.in_config_, true);           // 2 param
        EXPECT_EQ(s1.presented_, true);           // default
    }
    {
        StateVector states;
        LogWatchEntry lwe;
        // new entry
        lwe.init("a", "off", false);
        AddConfigEntry(states, lwe, false);
        {
            auto &s = states.back();
            EXPECT_EQ(s.name_, std::string("a"));
            EXPECT_EQ(s.in_config_, true);
            EXPECT_EQ(s.hide_context_, true);
            EXPECT_EQ(s.presented_, true);
            EXPECT_EQ(s.pos_, cfg::kFromBegin);
            EXPECT_EQ(s.level_, cfg::EventLevels::kOff);
        }

        lwe.init("a", "warn", true);
        AddConfigEntry(states, lwe, true);
        {
            auto &s = states.back();
            EXPECT_EQ(s.name_, std::string("a"));
            EXPECT_EQ(s.hide_context_, false);   // changed
            EXPECT_EQ(s.presented_, true);       // no change
            EXPECT_EQ(s.pos_, cfg::kFromBegin);  // no change
            EXPECT_EQ(s.level_, cfg::EventLevels::kWarn);
        }

        lwe.init("b", "crit", true);
        AddConfigEntry(states, lwe, true);
        {
            auto &s = states.back();
            EXPECT_EQ(states.size(), 2);
            EXPECT_EQ(s.name_, std::string("b"));
            EXPECT_EQ(s.in_config_, true);
            EXPECT_EQ(s.hide_context_, false);
            EXPECT_EQ(s.presented_, true);
            EXPECT_EQ(s.pos_, 0);
            EXPECT_EQ(s.level_, cfg::EventLevels::kCrit);
        }
    }
}

TEST(LogWatchEventTest, CheckMakeBodyIntegration) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    LogWatchEvent lw;
    lw.loadConfig();
    auto ret = lw.makeBody();
    ret = lw.makeBody();
    EXPECT_TRUE(ret.size() < 2000) << "should be almost empty";
    auto table = tools::SplitString(ret, "\n");
    auto old_size = table.size();
    ret = lw.makeBody();
    EXPECT_TRUE(!ret.empty());
    EXPECT_TRUE(ret.size() < 6000);
    table = tools::SplitString(ret, "\n");
    EXPECT_LE(table.size(), old_size * 2);
}

TEST(LogWatchEventTest, TestDefaultEntry) {
    {
        StateVector st;
        st.emplace_back("Abc");
        LogWatchEvent lw;
        LogWatchEntry dflt_entry = GenerateDefaultValue();
        LogWatchEntry entry;
        entry.loadFrom("'*': warn context");
        EXPECT_EQ(dflt_entry.name(), entry.name());
        EXPECT_EQ(dflt_entry.level(), entry.level());
        EXPECT_EQ(dflt_entry.context(), entry.context());

        lw.entries_.push_back(entry);
        lw.default_entry_ = 0;
        UpdateStatesByConfig(st, lw.entries(), lw.defaultEntry());
        EXPECT_EQ(st[0].in_config_, true);
        EXPECT_EQ(st[0].level_, cfg::EventLevels::kWarn);
        EXPECT_EQ(st[0].hide_context_, false);
    }

    {
        StateVector st;
        st.emplace_back("Abc");
        LogWatchEvent lw;
        LogWatchEntry entry;
        entry.loadFrom("'*': off context");
        lw.entries_.push_back(entry);
        lw.default_entry_ = 0;
        UpdateStatesByConfig(st, lw.entries(), lw.defaultEntry());
        EXPECT_EQ(st[0].in_config_, false);
        EXPECT_EQ(st[0].level_, cfg::EventLevels::kOff);
        EXPECT_EQ(st[0].hide_context_, false);
    }
}

TEST(LogWatchEventTest, TestMakeBody) {
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    auto cfg = cfg::GetLoadedConfig();
    LoadTestConfig(cfg);

    LogWatchEvent lwe;
    auto statefiles = lwe.makeStateFilesTable();
    ASSERT_EQ(statefiles.size(), 1);
    ASSERT_EQ(statefiles[0].u8string().empty(), false);

    lwe.loadConfig();
    ASSERT_TRUE(lwe.defaultEntry());
    auto def = lwe.defaultEntry();
    EXPECT_EQ(def->name(), "*");

    bool send_all = lwe.sendAll();
    auto states = details::LoadEventlogOffsets(statefiles,
                                               send_all);  // offsets stored

    states.push_back(State("zzz", 1, false));

    // check by registry, which logs are presented
    auto logs_in_registry = GatherEventLogEntriesFromRegistry();
    ASSERT_TRUE(logs_in_registry.size() > 5);

    {
        auto st = states;
        auto logs_in = logs_in_registry;
        logs_in.push_back("Zcx");
        auto processed = UpdateEventLogStates(st, logs_in, SendMode::normal);
        EXPECT_TRUE(processed == logs_in.size());
        int count = 0;
        for (auto &s : st) {
            auto found = std::find(logs_in.cbegin(), logs_in.cend(), s.name_);
            if (found == std::end(logs_in)) {
                EXPECT_FALSE(s.presented_);

            } else {
                count++;
                EXPECT_TRUE(s.presented_);
                if (std::string("Zcx") == s.name_) {
                    EXPECT_TRUE(s.pos_ == cfg::kFromBegin);
                }
            }
        }
        EXPECT_EQ(count, logs_in.size());  // all must be inside
    }

    {
        auto st = states;
        std::vector<std::string> logs_in;
        logs_in.push_back("Zcx");
        auto processed = UpdateEventLogStates(st, logs_in, SendMode::all);
        EXPECT_EQ(processed, 1);
        int count = 0;
        for (auto &s : st) {
            auto found = std::find(logs_in.cbegin(), logs_in.cend(), s.name_);
            if (found == std::end(logs_in)) {
                EXPECT_FALSE(s.presented_);

            } else {
                count++;
                EXPECT_TRUE(s.presented_);
                if (std::string("Zcx") == s.name_) {
                    EXPECT_TRUE(s.pos_ == 0);
                }
            }
        }
        EXPECT_EQ(count, logs_in.size());  // all must be inside
    }

    auto processed =
        UpdateEventLogStates(states, logs_in_registry, SendMode::normal);

    int application_index = -1;
    int system_index = -1;
    bool security_found = false;
    int index = 0;
    for (auto &s : states) {
        if (s.name_ == std::string("Application")) application_index = index;
        if (s.name_ == std::string("System")) system_index = index;
        if (s.name_ == std::string("Security")) security_found = true;
        if (s.name_ == std::string("zzz")) {
            EXPECT_EQ(s.pos_, 1);  // this is simulated
        }
        EXPECT_EQ(s.level_, cfg::EventLevels::kCrit);
        EXPECT_EQ(s.hide_context_, true);
        index++;
    }
    ASSERT_TRUE(application_index != -1);
    ASSERT_TRUE(system_index != -1);
    EXPECT_TRUE(security_found);

    int demo_index = -1;
    {
        // add Demo
        for (auto &e : lwe.entries())
            AddLogState(states, true, e.name(), SendMode::normal);

        for (auto &s : states) {
            if (s.name_ == std::string("Demo")) demo_index = index;
        }

        ASSERT_TRUE(demo_index != -1);
    }

    UpdateStatesByConfig(states, lwe.entries(), lwe.defaultEntry());
    EXPECT_EQ(states[application_index].in_config_, true);
    EXPECT_EQ(states[system_index].in_config_, true);
    EXPECT_EQ(states[demo_index].in_config_, true);
    EXPECT_EQ(states[demo_index].pos_, cfg::kFromBegin);

    EXPECT_EQ(states[application_index].hide_context_, false);
    EXPECT_EQ(states[application_index].level_, cfg::EventLevels::kCrit);

    EXPECT_EQ(states[system_index].hide_context_, true);
    EXPECT_EQ(states[system_index].level_, cfg::EventLevels::kWarn);

    lwe.updateSectionStatus();
    auto result = lwe.generateContent();
    EXPECT_TRUE(!result.empty());
    if (lwe.sendAll()) {
        EXPECT_TRUE(result.size() > 100000);
    } else {
        XLOG::l(XLOG::kStdio |
                XLOG::kInfo)("Test is SKIPPED due to installation settings");
        EXPECT_TRUE(result.size() > 30);
    }
}

TEST(LogWatchEventTest, RegPresence) {
    EXPECT_EQ(true, IsEventLogInRegistry("Application"));
    EXPECT_EQ(true, IsEventLogInRegistry("System"));
    EXPECT_EQ(true, IsEventLogInRegistry("Security"));

    EXPECT_EQ(false, IsEventLogInRegistry("Demo"));
    EXPECT_EQ(false, IsEventLogInRegistry(""));
}

TEST(LogWatchEventTest, TestNotSendAll) {
    // we are loading special test config with more or less custom data
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    auto cfg = cfg::GetLoadedConfig();
    LoadTestConfig(cfg);

    auto x = cfg[cfg::groups::kLogWatchEvent];
    auto old = x[cfg::vars::kLogWatchEventSendall].as<bool>(false);
    x[cfg::vars::kLogWatchEventSendall] = false;

    LogWatchEvent lwe;
    lwe.loadConfig();
    lwe.updateSectionStatus();
    auto result = lwe.generateContent();
    XLOG::l(XLOG::kEvent)("EventLog <GTEST>");
    lwe.loadConfig();
    lwe.updateSectionStatus();
    result = lwe.generateContent();
    EXPECT_TRUE(!result.empty());
    EXPECT_TRUE(result.size() < 100000);
    EXPECT_TRUE(result.find("EventLog <GTEST>") != std::string::npos);
    // printf("OUTPUT:\n%s\n", result.c_str());

    x[cfg::vars::kLogWatchEventSendall] = old;
}

TEST(LogWatchEventTest, TestNotSendAllVista) {
    // we are loading special test config with more or less custom data
    auto temp_fs = tst::TempCfgFs::CreateNoIo();
    auto cfg = cfg::GetLoadedConfig();
    LoadTestConfig(cfg);

    auto x = cfg[cfg::groups::kLogWatchEvent];
    auto old = x[cfg::vars::kLogWatchEventSendall].as<bool>(false);
    x[cfg::vars::kLogWatchEventSendall] = false;

    auto old_vista = x[cfg::vars::kLogWatchEventVistaApi].as<bool>(false);
    x[cfg::vars::kLogWatchEventVistaApi] = true;

    {
        LogWatchEvent lwe;
        lwe.loadConfig();
        lwe.generateContent();
    }
    XLOG::l(XLOG::kEvent)("EventLog Vista <GTEST>");
    LogWatchEvent lwe;
    lwe.loadConfig();
    auto result = lwe.generateContent();
    XLOG::l(XLOG::kEvent)("EventLog Vista <GTEST>");
    result = lwe.generateContent();
    EXPECT_TRUE(!result.empty());
    EXPECT_TRUE(result.size() < 100000);
    EXPECT_TRUE(result.find("EventLog Vista <GTEST>") != std::string::npos);
    // printf("OUTPUT:\n%s\n", result.c_str());

    x[cfg::vars::kLogWatchEventSendall] = old;
    x[cfg::vars::kLogWatchEventVistaApi] = old_vista;
}

TEST(LogWatchEventTest, TestSkip) {
    auto test_fs = tst::TempCfgFs::Create();
    ASSERT_TRUE(test_fs->loadFactoryConfig());
    auto cfg = cfg::GetLoadedConfig();
    auto x = cfg[cfg::groups::kLogWatchEvent];
    x[cfg::vars::kLogWatchEventSkip] = true;
    {
        LogWatchEvent lwe;
        lwe.loadConfig();
        lwe.generateContent();
    }
    auto text = fmt::format("EventLog {} <GTEST>", ::GetCurrentProcessId());
    XLOG::l(XLOG::kEvent)(text);
    XLOG::l(XLOG::kEvent)(text);
    LogWatchEvent lwe;
    lwe.loadConfig();
    auto result = lwe.generateContent();
    EXPECT_TRUE(result.find(text) != std::string::npos);
    EXPECT_TRUE(result.find(fmt::format(evl::kSkippedMessageFormat, 1)) !=
                std::string::npos);

    x[cfg::vars::kLogWatchEventSkip] = false;
    XLOG::l(XLOG::kEvent)(text);
    XLOG::l(XLOG::kEvent)(text);
    lwe.loadConfig();
    result = lwe.generateContent();
    auto pos = result.find(text);
    EXPECT_TRUE(pos != std::string::npos);
    EXPECT_TRUE(result.substr(pos).find(text) != std::string::npos);
    EXPECT_TRUE(result.find(fmt::format(evl::kSkippedMessageFormat, 1)) ==
                std::string::npos);
}

}  // namespace cma::provider
