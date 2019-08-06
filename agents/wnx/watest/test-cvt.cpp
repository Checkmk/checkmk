// test-cvt.cpp :
// ini -> yml

#include "pch.h"

#include <filesystem>

#include "cvt.h"
#include "lwa/types.h"
#include "providers/logwatch_event.h"
#include "providers/mrpe.h"
#include "read_file.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"
#include "yaml-cpp/yaml.h"

template <class T>
std::string type_name() {
    typedef typename std::remove_reference<T>::type TR;
    std::unique_ptr<char, void (*)(void*)> own(
#ifndef _MSC_VER
        abi::__cxa_demangle(typeid(TR).name(), nullptr, nullptr, nullptr),
#else
        nullptr,
#endif
        std::free);
    std::string r = own != nullptr ? own.get() : typeid(TR).name();
    if (std::is_const<TR>::value) r += " const";
    if (std::is_volatile<TR>::value) r += " volatile";
    if (std::is_lvalue_reference<T>::value)
        r += "&";
    else if (std::is_rvalue_reference<T>::value)
        r += "&&";
    return r;
}

// clang-format off
//  { "global", "port", int},
//  { "global", "realtime_port", int},
//  { "global", "realtime_timeout", int},
//  { "global", "crash_debug", bool},
//  { "global", "section_flush", bool},
//  { "global", "encrypted", bool},
//  { "global", "encrypted_rt", bool},
//  { "global", "ipv6", bool},
//  { "global", "passphrase", std::string}
//  { "global", "logging", std::string},
//  { "global", "remove_legacy", bool},


// SPLITTED LIST of ipspec
//  { "global", "only_from", std::vector<ipspec>,                BlockMode::FileExclusive, AddMode::Append}

// SPLITTED LIST of strings
// { "global", "sections", std::set<class std::string>,          BlockMode::BlockExclusive, AddMode::SetInserter}
// { "global", "disabled_sections", std::set<class std::string>, BlockMode::BlockExclusive, AddMode::SetInserter}
// { "global", "realtime_sections", std::set<class std::string>, BlockMode::BlockExclusive, AddMode::SetInserter}

// NOT USED
//{ "local", "include",  KeyedListConfigurable<std::string> }
//{ "plugin", "include", KeyedListConfigurable<std::string> }


// { "winperf", "counters", class std::vector<struct winperf_counter>, class BlockMode::Nop, class AddMode::Append}

// { "ps",     "use_wmi",    bool }
// { "ps",     "full_path",  bool }


// { "fileinfo", "path", class std::vector<std::filesystem::path>, class BlockMode::Nop, class AddMode::PriorityAppend }

// { "logwatch", "sendall",   bool}
// { "logwatch", "vista_api", bool}

// { "logwatch", "logname", std::vector<eventlog::config>, BlockMode::Nop, AddMode::PriorityAppend}
// { "logwatch", "logfile", std::vector<eventlog::config>, BlockMode::Nop, AddMode::PriorityAppend}


// { "logfiles", "textfile", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}
// { "logfiles", "warn", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}
// { "logfiles", "crit", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}
// { "logfiles", "ignore", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}
// { "logfiles", "ok", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}

// { "global", "caching_method", class Configurable<enum script_execution_mode>& Value}
// { "global", "async_script_execution", class Configurable<enum script_async_execution>& Value}


// { "global", "execute", <std::vector<std::string>, class BlockMode::BlockExclusive, class AddMode::Append}

// { "local", "timeout", class KeyedListConfigurable<int>}
// { "local", "cache_age", class KeyedListConfigurable<int>}
// { "local", "retry_count", class KeyedListConfigurable<int>}
// { "local", "execution", class KeyedListConfigurable<enum script_execution_mode>}


// { "mrpe", "check", std::vector<mrpe_entry>, BlockMode::Nop, AddMode::Append }
// { "mrpe", "include", KeyedListConfigurable<std::string>}
// clang-format on

#include "cvt.h"

template <typename T>
void printType(T x) {
    std::cout << type_name<T>();
}

namespace cma::cfg::cvt {

void AddKeyedPattern(YAML::Node Node, const std::string Key,
                     const std::string& Pattern, const std::string& Value);

TEST(CvtTest, Keyed) {
    auto result = ToYamlKeyedString("key", "pattern", "0");
    EXPECT_EQ(result, "pattern: 'pattern'\nkey: 0");

    YAML::Node y;
    y["plugins"]["enabled"] = true;
    auto y_exec = y["execution"];

    AddKeyedPattern(y_exec, "k1", "p1", "v1");
    AddKeyedPattern(y_exec, "k2", "p1", "v2");
    AddKeyedPattern(y_exec, "k1", "p2", "v1");
    ASSERT_EQ(y_exec.size(), 2);
    EXPECT_EQ(y_exec[0]["pattern"].as<std::string>(), "p1");
    EXPECT_EQ(y_exec[0]["k1"].as<std::string>(), "v1");
    EXPECT_EQ(y_exec[0]["k2"].as<std::string>(), "v2");
    EXPECT_EQ(y_exec[1]["pattern"].as<std::string>(), "p2");
    EXPECT_EQ(y_exec[1]["pattern"].as<std::string>(), "p2");
    EXPECT_EQ(y_exec[1]["k1"].as<std::string>(), "v1");
}  // namespace cma::cfg::cvt

TEST(CvtTest, ToYaml) {
    winperf_counter z(0, "this_name", "this base id");

    auto s = ToYamlString(z, false);
    EXPECT_EQ(s, "- this base id: this_name\n");

    auto s2 = ToYamlString("aaaa", false);
    EXPECT_EQ(s2, "aaaa");

    auto s3 = ToYamlString("aaaa", true);
    EXPECT_EQ(s3, "- aaaa");
}

TEST(CvtTest, LogFilesSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.logfiles.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kLogFiles].IsMap());
        auto logfiles = ya[groups::kLogFiles];
        ASSERT_TRUE(logfiles.IsMap());
        EXPECT_TRUE(logfiles[vars::kEnabled].as<bool>());

        EXPECT_TRUE(logfiles[vars::kLogFilesConfig].size() == 6);
        auto cfgs = logfiles[vars::kLogFilesConfig];

        EXPECT_TRUE(!cfgs[0][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[1][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[2][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[3][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[4][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[5][vars::kLogFilesGlob].as<std::string>().empty());

        EXPECT_TRUE(!cfgs[0][vars::kLogFilesPattern].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[1][vars::kLogFilesPattern].as<std::string>().empty());
        EXPECT_TRUE(cfgs[2][vars::kLogFilesPattern].IsNull());
        EXPECT_TRUE(cfgs[3][vars::kLogFilesPattern].IsNull());
        EXPECT_TRUE(cfgs[4][vars::kLogFilesPattern].IsNull());
        EXPECT_TRUE(cfgs[5][vars::kLogFilesPattern].IsNull());
    }
}

TEST(CvtTest, LogWatchSection) {
    namespace fs = std::filesystem;
    using namespace cma::cfg;
    using namespace cma::provider;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.logwatch.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kLogWatchEvent].IsMap());
        auto logwatch = ya[groups::kLogWatchEvent];
        ASSERT_TRUE(logwatch.IsMap());
        EXPECT_TRUE(logwatch[vars::kEnabled].as<bool>());
        EXPECT_TRUE(logwatch[vars::kLogWatchEventSendall].as<bool>());
        EXPECT_TRUE(logwatch[vars::kLogWatchEventVistaApi].as<bool>());

        ASSERT_TRUE(logwatch[vars::kLogWatchEventLogFile].size() == 4);
        auto logfiles = logwatch[vars::kLogWatchEventLogFile];
        const RawLogWatchData base[4] = {
            {true, "application", EventLevels::kCrit, true},
            {true, "system", EventLevels::kWarn, false},
            {true, "*", EventLevels::kOff, true},
            {true, "microsoft-windows-grouppolicy/operational",
             EventLevels::kWarn, true},
        };

        for (int i = 0; i < 4; ++i) {
            LogWatchEntry lwe;
            lwe.loadFromMapNode(logfiles[i]);
            EXPECT_EQ(lwe.name(), base[i].name_);
            EXPECT_EQ(lwe.level(), base[i].level_);
            EXPECT_EQ(lwe.context(), base[i].context_);
            EXPECT_EQ(lwe.loaded(), base[i].loaded_);
        }
    }
}

TEST(CvtTest, MrpeSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.mrpe.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kMrpe].IsMap());
        auto mr = ya[groups::kMrpe];
        ASSERT_TRUE(mr.IsMap());
        EXPECT_TRUE(mr[vars::kEnabled].as<bool>());
        EXPECT_TRUE(mr[vars::kMrpeConfig].IsSequence());
        EXPECT_TRUE(mr[vars::kMrpeConfig].size() == 5);
        EXPECT_TRUE(mr[vars::kMrpeConfig].size() == 5);
    }
    cma::provider::MrpeProvider mrpe;
    mrpe.loadConfig();
    auto entries = mrpe.entries();
    ASSERT_EQ(entries.size(), 3);
    auto checks = mrpe.checks();
    ASSERT_EQ(checks.size(), 3);
    auto includes = mrpe.includes();
    ASSERT_EQ(includes.size(), 2);
}

TEST(CvtTest, PluginsLocalSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.plugins_local.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kLocal].IsMap());
        auto loc = ya[groups::kLocal];
        ASSERT_TRUE(loc.IsMap());
        EXPECT_TRUE(loc[vars::kEnabled].as<bool>());
        EXPECT_TRUE(loc[vars::kPluginsExecution].IsSequence());
        EXPECT_TRUE(loc[vars::kPluginsExecution].size() == 3);
        auto exec = loc[vars::kPluginsExecution];
        EXPECT_EQ(exec[0][vars::kPluginPattern].as<std::string>(), "*.vbs");
        EXPECT_EQ(exec[1][vars::kPluginPattern].as<std::string>(), "*.bat");
        EXPECT_EQ(exec[2][vars::kPluginPattern].as<std::string>(), "*");

        EXPECT_EQ(exec[0][vars::kPluginTimeout].as<int>(), 20);
        EXPECT_EQ(exec[1][vars::kPluginTimeout].as<int>(), 10);
        EXPECT_EQ(exec[2][vars::kPluginTimeout].as<int>(), 30);
    }
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kLocal].IsMap());
        auto plu = ya[groups::kPlugins];
        ASSERT_TRUE(plu.IsMap());
        EXPECT_TRUE(plu[vars::kEnabled].as<bool>());
        EXPECT_TRUE(plu[vars::kPluginsExecution].IsSequence());
        EXPECT_EQ(plu[vars::kPluginsExecution].size(), 5);
        auto exec = plu[vars::kPluginsExecution];
        EXPECT_EQ(exec[0][vars::kPluginPattern].as<std::string>(),
                  std::string(yml_var::kUserPlugins) + "\\windows_updates.vbs");
        EXPECT_EQ(exec[1][vars::kPluginPattern].as<std::string>(),
                  std::string(yml_var::kUserPlugins) + "\\mk_inventory.ps1");
        EXPECT_EQ(exec[2][vars::kPluginPattern].as<std::string>(),
                  std::string(yml_var::kUserPlugins) + "\\ps_perf.ps1");
        EXPECT_EQ(exec[3][vars::kPluginPattern].as<std::string>(),
                  std::string(yml_var::kUserPlugins) + "\\*.ps1");
        EXPECT_EQ(exec[4][vars::kPluginPattern].as<std::string>(),
                  std::string(yml_var::kUserPlugins) + "\\*");

        EXPECT_EQ(exec[0][vars::kPluginTimeout].as<int>(), 120);
        EXPECT_EQ(exec[0][vars::kPluginCacheAge].as<int>(), 3600);
        EXPECT_EQ(exec[0][vars::kPluginRetry].as<int>(), 3);
        EXPECT_EQ(exec[0][vars::kPluginAsync].as<bool>(), true);

        EXPECT_EQ(exec[1][vars::kPluginTimeout].as<int>(), 240);
        EXPECT_EQ(exec[1][vars::kPluginAsync].as<bool>(), true);

        EXPECT_EQ(exec[2][vars::kPluginTimeout].as<int>(), 20);
        EXPECT_EQ(exec[3][vars::kPluginTimeout].as<int>(), 10);
        EXPECT_EQ(exec[4][vars::kPluginTimeout].as<int>(), 30);
    }
}

TEST(CvtTest, PsSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.ps.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kPs].IsMap());
        auto ps = ya[groups::kPs];
        ASSERT_TRUE(ps.IsMap());
        {
            EXPECT_FALSE(ps[vars::kPsFullPath].as<bool>());
            EXPECT_FALSE(ps[vars::kPsUseWmi].as<bool>());
            EXPECT_TRUE(ps[vars::kEnabled].as<bool>());
        }
    }
}

TEST(CvtTest, FileInfoSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.fileinfo.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kFileInfo].IsMap());
        auto fi = ya[groups::kFileInfo];
        ASSERT_TRUE(fi.IsMap());
        {
            auto paths = fi[vars::kFileInfoPath];
            ASSERT_TRUE(paths.IsSequence());
            ASSERT_TRUE(paths.size() == 3);
            EXPECT_EQ(paths[0].as<std::string>(), "C:\\Programs\\Foo\\*.log");
            EXPECT_EQ(paths[1].as<std::string>(), "M:\\Bar Test\\*.*");
            EXPECT_EQ(paths[2].as<std::string>(), "C:\\MyDocuments\\Foo\\**");
            EXPECT_TRUE(fi[vars::kEnabled].as<bool>());
        }
    }
}

TEST(CvtTest, WinPerfSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.winperf.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kWinPerf].IsMap());
        auto wp = ya[groups::kWinPerf];
        ASSERT_TRUE(wp.IsMap());
        {
            auto counters_raw = wp[vars::kWinPerfCounters];
            ASSERT_TRUE(counters_raw.IsSequence());
            ASSERT_TRUE(counters_raw.size() == 3);
            auto counters =
                GetPairArray(groups::kWinPerf, vars::kWinPerfCounters);

            EXPECT_EQ(counters[0].first, "10332");
            EXPECT_EQ(counters[0].second, "msx_queues");
            EXPECT_EQ(counters[1].first, "638");
            EXPECT_EQ(counters[1].second, "tcp_conn");
            EXPECT_EQ(counters[2].first, "Terminal Services");
            EXPECT_EQ(counters[2].second, "ts_sessions");
            EXPECT_TRUE(wp[vars::kEnabled].as<bool>());
        }
    }
}

TEST(CvtTest, GlobalSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.global.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kGlobal].IsMap());
        auto g = ya[groups::kGlobal];
        ASSERT_TRUE(g.IsMap());
        EXPECT_EQ(g["async_script_execution"].as<std::string>(), "parallel");
        EXPECT_EQ(g[vars::kEnabled].as<bool>(), true);
        {
            auto logging = g[vars::kLogging];
            ASSERT_TRUE(logging.IsMap());
            EXPECT_EQ(logging[vars::kLogDebug].as<std::string>(), "yes");
        }
        {
            auto sections = GetInternalArray(g, vars::kSectionsEnabled);
            ASSERT_TRUE(sections.size() == 2);
            EXPECT_EQ(sections[0], "check_mk");
            EXPECT_EQ(sections[1], groups::kWinPerf);
        }
        {
            auto sessions = cma::cfg::GetInternalArray(groups::kGlobal,
                                                       vars::kSectionsDisabled);
            ASSERT_TRUE(sessions.size() == 2);

            EXPECT_TRUE(sessions[0] == "badname" || sessions[1] == "badname");
            EXPECT_TRUE(sessions[0] == groups::kLogFiles ||
                        sessions[1] == groups::kLogFiles);
        }
        {
            auto onlyfrom = GetInternalArray(g, vars::kOnlyFrom);

            ASSERT_TRUE(onlyfrom.size() == 3);
            EXPECT_EQ(onlyfrom[0], "127.0.0.1/32");
            EXPECT_EQ(onlyfrom[1], "192.168.56.0/24");
            EXPECT_EQ(onlyfrom[2], "0:0:0:0:0:0:0:1/128");
        }
        {
            auto execute =
                cma::cfg::GetInternalArray(groups::kGlobal, vars::kExecute);
            ASSERT_TRUE(execute.size() == 3);
            EXPECT_EQ(execute[0], "exe");
            EXPECT_EQ(execute[1], "bat");
            EXPECT_EQ(execute[2], "vbs");
        }

        {
            EXPECT_EQ(g[vars::kGlobalEncrypt].as<bool>(), false);
            EXPECT_EQ(g[vars::kGlobalPassword].as<std::string>(), "secret");
            EXPECT_EQ(g[vars::kSectionFlush].as<bool>(), false);
            EXPECT_EQ(g[vars::kPort].as<int>(), 6556);
            EXPECT_EQ(g[vars::kIpv6].as<bool>(), false);
            EXPECT_EQ(g[vars::kGlobalRemoveLegacy].as<bool>(), true);
        }

        {
            auto rt = g[vars::kRealTime];
            ASSERT_TRUE(rt.IsMap());
            EXPECT_EQ(rt[vars::kEnabled].as<bool>(), true);
            EXPECT_EQ(rt[vars::kTimeout].as<int>(), 90);
            EXPECT_EQ(rt[vars::kRtEncrypt].as<bool>(), true);
            auto rt_sessions = GetInternalArray(rt, vars::kRtRun);
            ASSERT_TRUE(rt_sessions.size() == 3);
            EXPECT_EQ(rt_sessions[0], "df");
            EXPECT_EQ(rt_sessions[1], "mem");
            EXPECT_EQ(rt_sessions[2], "winperf_processor");
        }
    }
}

TEST(CvtTest, GlobalSectionOld) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.global.old.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(AppType::test, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(AppType::test));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kGlobal].IsMap());
        auto g = ya[groups::kGlobal];
        ASSERT_TRUE(g.IsMap());
        EXPECT_EQ(g["async_script_execution"].as<std::string>(), "parallel");
        EXPECT_EQ(g[vars::kEnabled].as<bool>(), true);
        {
            auto logging = g[vars::kLogging];
            ASSERT_TRUE(logging.IsMap());
            EXPECT_EQ(logging[vars::kLogDebug].as<std::string>(), "yes");
        }
        {
            auto sections = GetInternalArray(g, vars::kSectionsEnabled);
            ASSERT_TRUE(sections.size() == 2);
            EXPECT_EQ(sections[0], "check_mk");
            EXPECT_EQ(sections[1], groups::kWinPerf);
        }
        {
            auto sessions = cma::cfg::GetInternalArray(groups::kGlobal,
                                                       vars::kSectionsDisabled);
            ASSERT_TRUE(sessions.size() == 2);

            EXPECT_TRUE(sessions[0] == "badname" || sessions[1] == "badname");
            EXPECT_TRUE(sessions[0] == groups::kLogFiles ||
                        sessions[1] == groups::kLogFiles);
        }
        {
            auto onlyfrom = GetInternalArray(g, vars::kOnlyFrom);

            ASSERT_TRUE(onlyfrom.size() == 3);
            EXPECT_EQ(onlyfrom[0], "127.0.0.1/32");
            EXPECT_EQ(onlyfrom[1], "192.168.56.0/24");
            EXPECT_EQ(onlyfrom[2], "0:0:0:0:0:0:0:1/128");
        }
        {
            auto execute =
                cma::cfg::GetInternalArray(groups::kGlobal, vars::kExecute);
            ASSERT_TRUE(execute.size() == 3);
            EXPECT_EQ(execute[0], "exe");
            EXPECT_EQ(execute[1], "bat");
            EXPECT_EQ(execute[2], "vbs");
        }

        {
            EXPECT_EQ(g[vars::kGlobalEncrypt].as<bool>(), false);
            EXPECT_EQ(g[vars::kGlobalPassword].as<std::string>(), "secret");
            EXPECT_EQ(g[vars::kSectionFlush].as<bool>(), false);
            EXPECT_EQ(g[vars::kPort].as<int>(), 6556);
            EXPECT_EQ(g[vars::kIpv6].as<bool>(), false);
        }

        {
            auto rt = g[vars::kRealTime];
            ASSERT_TRUE(rt.IsMap());
            EXPECT_EQ(rt[vars::kEnabled].as<bool>(), true);
            EXPECT_EQ(rt[vars::kTimeout].as<int>(), 90);
            EXPECT_EQ(rt[vars::kRtEncrypt].as<bool>(), true);
            auto rt_sessions = GetInternalArray(rt, vars::kRtRun);
            ASSERT_TRUE(rt_sessions.size() == 3);
            EXPECT_EQ(rt_sessions[0], "df");
            EXPECT_EQ(rt_sessions[1], "mem");
            EXPECT_EQ(rt_sessions[2], "winperf_processor");
        }
    }
}

TEST(CvtTest, BaseCall) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.out";

    std::error_code ec;
    fs::remove(temp_file, ec);
    // ON_OUT_OF_SCOPE(fs::remove(temp_file, ec););
    std::ofstream out(temp_file);
    p.emitYaml(out);
    out.close();
    auto emitted = cma::tools::ReadFileInVector(temp_file);

    fs::path base_file = cma::cfg::GetUserDir();
    base_file /= "check_mk.test.out";
    ASSERT_TRUE(fs::exists(base_file, ec));

    auto expected = cma::tools::ReadFileInVector(base_file);
    EXPECT_EQ(emitted, expected);

    auto res = CheckIniFile(test_file);
    EXPECT_TRUE(res);

    auto yaml = p.emitYaml();
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    tst::SafeCleanTempDir();
}

}  // namespace cma::cfg::cvt
