// test-section-logwatch.cpp

//
#include "pch.h"

#include <filesystem>

#include "cfg.h"
#include "common/wtools.h"
#include "providers/logwatch_event.h"
#include "providers/logwatch_event_details.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"

namespace cma::provider {

static void LoadTestConfig(YAML::Node Node) {
    Node["logwatch"] = YAML::Load(
        "  enabled : yes\n"
        "  sendall : no\n"
        "  vista_api: no\n"
        "  logfile :\n"
        "    - 'Application': crit context\n"
        "    - 'System' : warn nocontext\n"
        "    - 'Demo' : all nocontext\n"
        "    - '': off nocontext\n"
        "    - '*' : warn context\n");
}

constexpr int LogWatchSections_Main = 2;
constexpr int LogWatchSections_Test = 5;

TEST(LogWatchEventTest, Consts) {
    using namespace std;
    using namespace cma::cfg;
    EXPECT_EQ(EventLevels::kOff, LabelToEventLevel({}));
    EXPECT_EQ(EventLevels::kOff, LabelToEventLevel(""));
    EXPECT_EQ(EventLevels::kOff, LabelToEventLevel("off"));
    EXPECT_EQ(EventLevels::kOff, LabelToEventLevel("off"));
    EXPECT_EQ(EventLevels::kWarn, LabelToEventLevel("warn"));
    EXPECT_EQ(EventLevels::kCrit, LabelToEventLevel("crit"));
    EXPECT_EQ(EventLevels::kAll, LabelToEventLevel("all"));
    EXPECT_EQ(EventLevels::kAll, LabelToEventLevel("alL"));
    EXPECT_EQ(EventLevels::kOff, LabelToEventLevel("all "));
}

TEST(LogWatchEventTest, LoadFrom) {
    using namespace std;
    using namespace cma::cfg;
    {
        LogWatchEntry lwe;
        lwe.loadFrom("  Abc :   ccc context ddd ");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), EventLevels::kOff);
        EXPECT_EQ(lwe.name(), "Abc");
        EXPECT_EQ(lwe.context(), true);
    }

    {
        LogWatchEntry lwe;
        lwe.loadFrom("  Abc :   warn ncontext ddd ");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), EventLevels::kWarn);
        EXPECT_EQ(lwe.name(), "Abc");
        EXPECT_EQ(lwe.context(), false);
    }

    {
        LogWatchEntry lwe;
        lwe.loadFrom("Abc:all context");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), EventLevels::kAll);
        EXPECT_EQ(lwe.name(), "Abc");
        EXPECT_EQ(lwe.context(), true);
    }

    {
        LogWatchEntry lwe;
        lwe.loadFrom("A :");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), EventLevels::kOff);
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
        EXPECT_EQ(lwe.level(), EventLevels::kCrit);
        EXPECT_EQ(lwe.name(), "*");
        EXPECT_EQ(lwe.context(), false);
    }
    {
        LogWatchEntry lwe;
        lwe.loadFrom(R"(' *  ' : crit nocontext )");
        EXPECT_TRUE(lwe.loaded());
        EXPECT_EQ(lwe.level(), EventLevels::kCrit);
        EXPECT_EQ(lwe.name(), "*");
        EXPECT_EQ(lwe.context(), false);
    }
}

TEST(LogWatchEventTest, Config) {
    using namespace std;
    using namespace cma::cfg;
    tst::YamlLoader w;
    {
        auto enabled = GetVal(groups::kLogWatchEvent, vars::kEnabled, false);
        EXPECT_EQ(enabled, true);
        auto vista_api =
            GetVal(groups::kLogWatchEvent, vars::kLogWatchEventVistaApi, false);
        EXPECT_EQ(vista_api, false);
        auto send_all =
            GetVal(groups::kLogWatchEvent, vars::kLogWatchEventSendall, false);
        EXPECT_EQ(send_all, false);

        auto sections =
            GetNode(groups::kLogWatchEvent, vars::kLogWatchEventLogFile);
        ASSERT_TRUE(sections.IsSequence());
        ASSERT_EQ(sections.size(), LogWatchSections_Main);

        // data to be tested against
        const RawLogWatchData base[LogWatchSections_Test] = {
            {false, "", cma::cfg::EventLevels::kOff, false},
            {true, "*", cma::cfg::EventLevels::kWarn, false},
        };

        int pos = 0;
        for (const auto& sec : sections) {
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
    }

    {
        auto cfg = cma::cfg::GetLoadedConfig();
        LoadTestConfig(cfg);
        auto enabled = GetVal(groups::kLogWatchEvent, vars::kEnabled, false);
        EXPECT_EQ(enabled, true);
        auto vista_api =
            GetVal(groups::kLogWatchEvent, vars::kLogWatchEventVistaApi, false);
        EXPECT_EQ(vista_api, false);
        auto send_all =
            GetVal(groups::kLogWatchEvent, vars::kLogWatchEventSendall, false);
        EXPECT_EQ(send_all, false);

        auto sections =
            GetNode(groups::kLogWatchEvent, vars::kLogWatchEventLogFile);
        ASSERT_TRUE(sections.IsSequence());
        ASSERT_EQ(sections.size(), LogWatchSections_Test);

        // data to be tested against
        const RawLogWatchData base[LogWatchSections_Test] = {
            {true, "Application", cma::cfg::EventLevels::kCrit, true},
            {true, "System", cma::cfg::EventLevels::kWarn, false},
            {true, "Demo", cma::cfg::EventLevels::kAll, false},
            {false, "", cma::cfg::EventLevels::kOff, false},
            {true, "*", cma::cfg::EventLevels::kWarn, true},
        };

        int pos = 0;
        for (const auto& sec : sections) {
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
    }
}

TEST(LogWatchEventTest, MakeStateFileName) {
    using namespace cma::provider;
    {
        auto x = MakeStateFileName("", "", "");
        EXPECT_TRUE(x.empty());
    }
    {
        auto x = MakeStateFileName("", ".a", "");
        EXPECT_TRUE(x.empty());
    }
    {
        auto x = MakeStateFileName("a", ".b", "");
        EXPECT_EQ(x, "a.b");
    }
    {
        auto x = MakeStateFileName("a", ".b", "1:2");
        EXPECT_EQ(x, "a_1_2.b");
    }
    {
        auto x = MakeStateFileName("a", ".b", "1::2:");
        EXPECT_EQ(x, "a_1__2_.b");
    }
}

TEST(LogWatchEventTest, ConfigStruct) {
    using namespace std;
    using namespace cma::cfg;
    {
        cma::provider::LogWatchEntry lwe;
        EXPECT_EQ(lwe.name(), "");
        EXPECT_TRUE(lwe.level() == cma::cfg::EventLevels::kOff);
        EXPECT_EQ(lwe.context(), false);
        EXPECT_EQ(lwe.loaded(), false);

        lwe.init("Name", "WARN", true);
        EXPECT_EQ(lwe.name(), "Name");
        EXPECT_TRUE(lwe.level() == cma::cfg::EventLevels::kWarn);
        EXPECT_EQ(lwe.context(), true);
        EXPECT_EQ(lwe.loaded(), true);
    }
    {
        cma::provider::LogWatchEntry lwe;
        lwe.init("Name", "off", true);
        EXPECT_TRUE(lwe.level() == cma::cfg::EventLevels::kOff);
    }
    {
        cma::provider::LogWatchEntry lwe;
        lwe.init("Name", "warn", false);
        EXPECT_TRUE(lwe.level() == cma::cfg::EventLevels::kWarn);
        EXPECT_FALSE(lwe.context());
    }
    {
        cma::provider::LogWatchEntry lwe;
        lwe.init("Name", "crit", true);
        EXPECT_TRUE(lwe.level() == cma::cfg::EventLevels::kCrit);
    }
    {
        cma::provider::LogWatchEntry lwe;
        lwe.init("Name", "all", true);
        EXPECT_TRUE(lwe.level() == cma::cfg::EventLevels::kAll);
    }

    tst::YamlLoader w;
    {
        auto cfg = cma::cfg::GetLoadedConfig();
        LoadTestConfig(cfg);
        auto enabled = GetVal(groups::kLogWatchEvent, vars::kEnabled, false);
        auto vista_api =
            GetVal(groups::kLogWatchEvent, vars::kLogWatchEventVistaApi, false);
        auto send_all =
            GetVal(groups::kLogWatchEvent, vars::kLogWatchEventSendall, false);

        auto sections =
            GetNode(groups::kLogWatchEvent, vars::kLogWatchEventLogFile);
        ASSERT_TRUE(sections.IsSequence());
        EXPECT_EQ(sections.size(), LogWatchSections_Test);
        {
            auto app = sections[0];
            ASSERT_TRUE(app.IsMap());

            cma::provider::LogWatchEntry lwe;
            lwe.loadFromMapNode(app);
            EXPECT_EQ(lwe.level(), cma::cfg::EventLevels::kCrit);
            EXPECT_EQ(lwe.context(), true);
            EXPECT_EQ(lwe.loaded(), true);
        }

        {
            auto sys = sections[1];
            ASSERT_TRUE(sys.IsMap());

            cma::provider::LogWatchEntry lwe;
            lwe.loadFromMapNode(sys);
            EXPECT_EQ(lwe.level(), cma::cfg::EventLevels::kWarn);
            EXPECT_EQ(lwe.context(), false);
            EXPECT_EQ(lwe.loaded(), true);
        }
        {
            auto demo = sections[2];
            ASSERT_TRUE(demo.IsMap());

            cma::provider::LogWatchEntry lwe;
            lwe.loadFromMapNode(demo);
            EXPECT_EQ(lwe.level(), cma::cfg::EventLevels::kAll);
            EXPECT_EQ(lwe.context(), false);
            EXPECT_EQ(lwe.loaded(), true);
        }
        {
            auto empty = sections[3];
            ASSERT_TRUE(empty.IsMap());

            cma::provider::LogWatchEntry lwe;
            lwe.loadFromMapNode(empty);
            EXPECT_EQ(lwe.level(), cma::cfg::EventLevels::kOff);
            EXPECT_EQ(lwe.context(), false);
            EXPECT_EQ(lwe.loaded(), false);
        }
    }
}

TEST(LogWatchEventTest, ConfigLoad) {
    using namespace std;
    using namespace cma::cfg;
    using namespace cma::provider;
    tst::YamlLoader w;

    {
        auto cfg = cma::cfg::GetLoadedConfig();
        LoadTestConfig(cfg);
        LogWatchEvent lw;
        lw.loadConfig();
        auto e = lw.entries();
        ASSERT_TRUE(e.size() > 2);
        EXPECT_TRUE(e[0].loaded());
        EXPECT_TRUE(e[1].loaded());
        EXPECT_TRUE(e[0].context() == true);
        EXPECT_TRUE(e[1].context() == false);
        EXPECT_EQ(e[0].name(), "Application");
        EXPECT_EQ(e[1].name(), "System");
        EXPECT_EQ(e[2].name(), "Demo");

        EXPECT_EQ(e[0].level(), cma::cfg::EventLevels::kCrit);
        EXPECT_EQ(e[1].level(), cma::cfg::EventLevels::kWarn);
        EXPECT_EQ(e[2].level(), cma::cfg::EventLevels::kAll);
    }
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
    using namespace std;
    using namespace cma::cfg;
    namespace fs = std::filesystem;

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
        for (auto& s : states) {
            EXPECT_FALSE(s.presented_);
            EXPECT_FALSE(s.name_.empty());
        }
    }

    {
        auto states = details::LoadEventlogOffsets(filelist, true);
        ASSERT_EQ(states.size(), 10);
        for (auto& s : states) {
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
    using namespace std;
    using namespace cma::cfg;

    StateVector states;
    AddLogState(states, false, "xxx", SendMode::normal);
    {
        auto& s0 = states[0];

        EXPECT_EQ(s0.hide_context_, true);                   // default
        EXPECT_EQ(s0.level_, cma::cfg::EventLevels::kCrit);  // default
        EXPECT_EQ(s0.pos_, cma::cfg::kInitialPos);           // 4 parameter
        EXPECT_EQ(s0.name_, std::string("xxx"));             // 3 param
        EXPECT_EQ(s0.in_config_, false);                     // 2 param
        EXPECT_EQ(s0.presented_, true);                      // default

        s0.presented_ = false;
        AddLogState(states, false, "xxx", SendMode::normal);
        EXPECT_EQ(s0.presented_, true);  // reset for found

        AddLogState(states, true, "xxx", SendMode::normal);
        EXPECT_EQ(s0.in_config_, true);  // reset with 2 param
    }

    {
        AddLogState(states, true, "yyy", SendMode::all);
        auto& s1 = states[1];
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
            auto& s = states.back();
            EXPECT_EQ(s.name_, std::string("a"));
            EXPECT_EQ(s.in_config_, true);
            EXPECT_EQ(s.hide_context_, true);
            EXPECT_EQ(s.presented_, true);
            EXPECT_EQ(s.pos_, cma::cfg::kInitialPos);
            EXPECT_EQ(s.level_, cma::cfg::EventLevels::kOff);
        }

        lwe.init("a", "warn", true);
        AddConfigEntry(states, lwe, true);
        {
            auto& s = states.back();
            EXPECT_EQ(s.name_, std::string("a"));
            EXPECT_EQ(s.hide_context_, false);         // changed
            EXPECT_EQ(s.presented_, true);             // no change
            EXPECT_EQ(s.pos_, cma::cfg::kInitialPos);  // no change
            EXPECT_EQ(s.level_, cma::cfg::EventLevels::kWarn);
        }

        lwe.init("b", "crit", true);
        AddConfigEntry(states, lwe, true);
        {
            auto& s = states.back();
            EXPECT_EQ(states.size(), 2);
            EXPECT_EQ(s.name_, std::string("b"));
            EXPECT_EQ(s.in_config_, true);
            EXPECT_EQ(s.hide_context_, false);
            EXPECT_EQ(s.presented_, true);
            EXPECT_EQ(s.pos_, 0);
            EXPECT_EQ(s.level_, cma::cfg::EventLevels::kCrit);
        }
    }
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
        EXPECT_EQ(st[0].level_, cma::cfg::EventLevels::kWarn);
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
        EXPECT_EQ(st[0].level_, cma::cfg::EventLevels::kOff);
        EXPECT_EQ(st[0].hide_context_, false);
    }
}

TEST(LogWatchEventTest, TestMakeBody) {
    using namespace std;
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    tst::YamlLoader w;
    auto cfg = cma::cfg::GetLoadedConfig();
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
    auto states =
        details::LoadEventlogOffsets(statefiles, send_all);  // offsets stored

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
        for (auto& s : st) {
            auto found = std::find(logs_in.cbegin(), logs_in.cend(), s.name_);
            if (found == std::end(logs_in)) {
                EXPECT_FALSE(s.presented_);

            } else {
                count++;
                EXPECT_TRUE(s.presented_);
                if (std::string("Zcx") == s.name_) {
                    EXPECT_TRUE(s.pos_ == cma::cfg::kInitialPos);
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
        for (auto& s : st) {
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
    for (auto& s : states) {
        if (s.name_ == std::string("Application")) application_index = index;
        if (s.name_ == std::string("System")) system_index = index;
        if (s.name_ == std::string("Security")) security_found = true;
        if (s.name_ == std::string("zzz")) {
            EXPECT_EQ(s.pos_, 1);  // this is simulated
        }
        EXPECT_EQ(s.level_, cma::cfg::EventLevels::kCrit);
        EXPECT_EQ(s.hide_context_, true);
        index++;
    }
    ASSERT_TRUE(application_index != -1);
    ASSERT_TRUE(system_index != -1);
    EXPECT_TRUE(security_found);

    int demo_index = -1;
    {
        // add Demo
        for (auto& e : lwe.entries())
            AddLogState(states, true, e.name(), SendMode::normal);

        for (auto& s : states) {
            if (s.name_ == std::string("Demo")) demo_index = index;
        }

        ASSERT_TRUE(demo_index != -1);
    }

    UpdateStatesByConfig(states, lwe.entries(), lwe.defaultEntry());
    EXPECT_EQ(states[application_index].in_config_, true);
    EXPECT_EQ(states[system_index].in_config_, true);
    EXPECT_EQ(states[demo_index].in_config_, true);
    EXPECT_EQ(states[demo_index].pos_, cma::cfg::kInitialPos);

    EXPECT_EQ(states[application_index].hide_context_, false);
    EXPECT_EQ(states[application_index].level_, cma::cfg::EventLevels::kCrit);

    EXPECT_EQ(states[system_index].hide_context_, true);
    EXPECT_EQ(states[system_index].level_, cma::cfg::EventLevels::kWarn);

    lwe.updateSectionStatus();
    auto result = lwe.generateContent(cma::section::kUseEmbeddedName);
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
    XLOG::l(XLOG::kEvent)("EventLog <GTEST>");
    using namespace std;
    using namespace cma::cfg;
    namespace fs = std::filesystem;

    // we are loading special test config with more or less custom data
    tst::YamlLoader w;
    auto cfg = cma::cfg::GetLoadedConfig();
    LoadTestConfig(cfg);

    auto x = cfg[groups::kLogWatchEvent];
    auto old = x[vars::kLogWatchEventSendall].as<bool>(false);
    x[vars::kLogWatchEventSendall] = false;

    LogWatchEvent lwe;
    lwe.loadConfig();
    lwe.updateSectionStatus();
    auto result = lwe.generateContent(cma::section::kUseEmbeddedName);
    EXPECT_TRUE(!result.empty());
    EXPECT_TRUE(result.size() < 100000);
    EXPECT_TRUE(result.find("EventLog <GTEST>") != std::string::npos);
    // printf("OUTPUT:\n%s\n", result.c_str());

    x[vars::kLogWatchEventSendall] = old;
}

TEST(LogWatchEventTest, TestNotSendAllVista) {
    XLOG::l(XLOG::kEvent)("EventLog Vista <GTEST>");
    using namespace std;
    using namespace cma::cfg;
    namespace fs = std::filesystem;

    // we are loading special test config with more or less custom data
    tst::YamlLoader w;
    auto cfg = cma::cfg::GetLoadedConfig();
    LoadTestConfig(cfg);

    auto x = cfg[groups::kLogWatchEvent];
    auto old = x[vars::kLogWatchEventSendall].as<bool>(false);
    x[vars::kLogWatchEventSendall] = false;

    auto old_vista = x[vars::kLogWatchEventVistaApi].as<bool>(false);
    x[vars::kLogWatchEventVistaApi] = true;

    LogWatchEvent lwe;
    lwe.loadConfig();
    auto result = lwe.generateContent(cma::section::kUseEmbeddedName);
    EXPECT_TRUE(!result.empty());
    EXPECT_TRUE(result.size() < 100000);
    EXPECT_TRUE(result.find("EventLog Vista <GTEST>") != std::string::npos);
    // printf("OUTPUT:\n%s\n", result.c_str());

    x[vars::kLogWatchEventSendall] = old;
    x[vars::kLogWatchEventVistaApi] = old_vista;
}

}  // namespace cma::provider
