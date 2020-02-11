// test-yaml.cpp :
// YAML and around

#include "pch.h"

#include <yaml-cpp/yaml.h>

#include <filesystem>

#include "cfg.h"
#include "cfg_details.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "providers/mrpe.h"
#include "read_file.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"

namespace cma::cfg::details {  // to become friendly for cma::cfg classes

static std::filesystem::path CreateYamlnInTemp(const std::string& Name,
                                               const std::string& Text) {
    namespace fs = std::filesystem;

    fs::path temp_folder = cma::cfg::GetTempDir();
    auto path = temp_folder / Name;

    std::ofstream ofs(path.u8string());

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", path.u8string(), GetLastError());
        return {};
    }

    ofs << Text << " \n";
    return path;
}

static std::filesystem::path CreateTestFile(const std::filesystem::path& Name,
                                            const std::string& Text) {
    namespace fs = std::filesystem;

    auto path = Name;

    std::ofstream ofs(path.u8string(), std::ios::binary);

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", path.u8string(), GetLastError());
        return {};
    }

    ofs << Text << "\n";
    return path;
}

#if 0
// memory tester
TEST(AgentConfig, MemoryLeaks) {
    for (auto i = 0; i < 100; i++) {
        OnStart(AppType::test);
        cma::provider::MrpeProvider m;
        m.generateContent(cma::section::kUseEmbeddedName);
        cma::tools::sleep(5000);
    }
}
#endif

TEST(AgentConfig, Folders) {
    ON_OUT_OF_SCOPE(cma::OnStart(AppType::test));
    cma::tools::win::SetEnv(std::wstring(kTemporaryRoot), std::wstring(L"."));
    cma::OnStart(AppType::exe);
    EXPECT_EQ(GetCfg().getRootDir().u8string(), ".");
    EXPECT_EQ(GetCfg().getUserDir().u8string(), "ProgramData\\checkmk\\agent");
}

TEST(AgentConfig, MainYaml) {
    auto root_dir = GetCfg().getRootDir();
    root_dir /= files::kDefaultMainConfig;
    auto load = YAML::LoadFile(root_dir.u8string());
    EXPECT_TRUE(load.IsMap());
    EXPECT_TRUE(load[groups::kGlobal].IsMap());
    EXPECT_TRUE(load[groups::kFileInfo].IsMap());
    EXPECT_TRUE(load[groups::kLocal].IsMap());
    EXPECT_FALSE(load[groups::kLogFiles].IsDefined()) << "logfiles"
                                                         " not supported";
    EXPECT_TRUE(load[groups::kLogWatchEvent].IsMap());
    EXPECT_TRUE(load[groups::kMrpe].IsMap());
    EXPECT_TRUE(load[groups::kPlugins].IsMap());
    EXPECT_TRUE(load[groups::kPs].IsMap());
    EXPECT_TRUE(load[groups::kWinPerf].IsMap());
}

// test helper, in fact calls MergeStringSequence
static std::string TestMergerSeq(const std::string& target,
                                 const std::string& source,
                                 const std::string& name) {
    auto user = YAML::Load(target);
    auto bakery = YAML::Load(source);
    MergeStringSequence(user, bakery, name);

    YAML::Emitter emit;
    emit << user;
    return emit.c_str();
}

// test helper, in fact calls MergeMapSequence
static YAML::Node TestMergerMap(const std::string& target,
                                const std::string& source,
                                const std::string& name,
                                const std::string& key) {
    auto user = YAML::Load(target);
    auto bakery = YAML::Load(source);

    MergeMapSequence(user, bakery, name, key);
    return user;
}

TEST(AgentConfig, AggregateSeq) {
    {
        // artificial but realistic data
        std::string empty = "plugins:\n  enabled: yes\n";
        std::string filled = "plugins:\n  folders: [a, b, c]";

        {
            YAML::Node target = YAML::Load(empty);
            YAML::Node source = YAML::Load(filled);
            auto source_size =
                source[groups::kPlugins][vars::kPluginsFolders].size();
            EXPECT_EQ(source_size, 3);
            EXPECT_TRUE(MergeStringSequence(target[groups::kPlugins],
                                            source[groups::kPlugins],
                                            vars::kPluginsFolders));
            EXPECT_EQ(target[groups::kPlugins][vars::kPluginsFolders].size(),
                      source_size)
                << "should have same size after merge";
        }

        {
            YAML::Node target = YAML::Load(filled);
            YAML::Node source = YAML::Load(empty);
            EXPECT_TRUE(MergeStringSequence(target[groups::kPlugins],
                                            source[groups::kPlugins],
                                            vars::kPluginsFolders));
            EXPECT_EQ(target[groups::kPlugins][vars::kPluginsFolders].size(), 3)
                << "should have same size after merge";
        }
    }
    {
        std::string tgt = "folders: [a, b, c, d]";
        std::string src = "folders: [b, c, e]";
        auto merged_yaml = TestMergerSeq(tgt, src, vars::kPluginsFolders);
        EXPECT_EQ("folders: [a, b, c, d, e]", merged_yaml);
    }

    {
        std::string tgt = "no_folders: weird";
        std::string src = "folders: [b, c, e]";
        auto merged_yaml = TestMergerSeq(tgt, src, vars::kPluginsFolders);
        EXPECT_EQ(tgt + "\n" + src, merged_yaml)
            << "target should concatenate source";
    }

    {
        std::string tgt = "folders: [a, b, c, d]";
        std::string src = "no_folders: weird";
        auto merged_yaml = TestMergerSeq(tgt, src, vars::kPluginsFolders);
        EXPECT_EQ(tgt, merged_yaml) << "target should be the same";
    }
}

TEST(AgentConfig, AggregateMap) {
    {
        // check for invalid nodes
        YAML::Node in;
        YAML::Node add;
        EXPECT_TRUE(MergeMapSequence(in, add, "a", "b"));
    }

    {
        // artificial but realistic data
        std::string empty =
            "plugins:\n"
            "  enabled: yes\n";

        std::string filled =
            "plugins:\n"
            "  execution:\n"
            "    - pattern: '$CUSTOM_PLUGINS_PATH$\\*.*'\n"
            "      timeout: 60\n"
            "      run: yes\n"
            "    - pattern: '$BUILTIN_PLUGINS_PATH$\\*.*'\n"
            "      timeout: 60\n"
            "      run: no\n"
            "    - pattern: '*'\n"
            "      timeout: 60\n"
            "      run: no\n";
        {
            // individual testing
        }

        {
            YAML::Node target = YAML::Load(empty);
            YAML::Node source = YAML::Load(filled);
            EXPECT_TRUE(MergeMapSequence(
                target[groups::kPlugins], source[groups::kPlugins],
                vars::kPluginsExecution, vars::kPluginPattern));
            EXPECT_EQ(target[groups::kPlugins][vars::kPluginsExecution].size(),
                      3)
                << "should be filled!";
        }

        {
            YAML::Node target = YAML::Load(filled);
            YAML::Node source = YAML::Load(empty);
            EXPECT_EQ(target[groups::kPlugins][vars::kPluginsExecution].size(),
                      3);
            EXPECT_TRUE(MergeMapSequence(
                target[groups::kPlugins], source[groups::kPlugins],
                vars::kPluginsExecution, vars::kPluginPattern));
            EXPECT_EQ(target[groups::kPlugins][vars::kPluginsExecution].size(),
                      3);
        }
    }

    {
        // artificial but realistic data
        std::string tgt =
            "  execution:\n"
            "    - pattern: '$CUSTOM_PLUGINS_PATH$\\windows_updates.vbs'\n"  // add
            "      cache_age: 14400\n"
            "      async: yes\n"
            "      timeout: 600\n"
            "    - pattern: '$BUILTIN_PLUGINS_PATH$\\*.*'\n"  // override
            "      timeout: 31\n"
            "      run: no\n";
        std::string src =
            "  execution:\n"
            "    - pattern: '$CUSTOM_PLUGINS_PATH$\\*.*'\n"
            "      timeout: 60\n"
            "      run: yes\n"
            "    - pattern: '$BUILTIN_PLUGINS_PATH$\\*.*'\n"
            "      timeout: 60\n"
            "      run: no\n"
            "    - pattern: '*'\n"
            "      timeout: 60\n"
            "      run: no\n";

        auto full_yaml = TestMergerMap(tgt, src, vars::kPluginsExecution,
                                       vars::kPluginPattern);
        auto merged_yaml = full_yaml[vars::kPluginsExecution];

        auto select = [merged_yaml](int index,
                                    const std::string& name) -> auto {
            return merged_yaml[index][name].as<std::string>();
        };

        ASSERT_TRUE(merged_yaml.IsSequence());
        ASSERT_EQ(merged_yaml.size(), 4);
        // from user
        ASSERT_EQ(select(0, vars::kPluginPattern),
                  "$CUSTOM_PLUGINS_PATH$\\windows_updates.vbs");

        EXPECT_EQ(select(1, vars::kPluginPattern),
                  std::string(yml_var::kBuiltinPlugins) + "\\*.*");
        EXPECT_EQ(select(1, vars::kPluginTimeout), "31");

        // merged from bakery(or system)
        EXPECT_EQ(select(2, vars::kPluginPattern),
                  "$CUSTOM_PLUGINS_PATH$\\*.*");
        EXPECT_EQ(select(3, vars::kPluginPattern), "*");
    }
}

TEST(AgentConfig, SmartMerge) {
    namespace fs = std::filesystem;
    std::wstring temporary_name = L"tmp_";
    temporary_name += files::kDefaultMainConfig;
    fs::path cfgs[] = {GetCfg().getRootDir() / temporary_name,
                       GetCfg().getBakeryDir() / temporary_name,
                       GetCfg().getUserDir() / temporary_name};
    cfgs[1].replace_extension("bakery.yml");
    cfgs[2].replace_extension("user.yml");

    std::error_code ec;
    ON_OUT_OF_SCOPE(for (auto& f : cfgs) fs::remove(f, ec););
    ON_OUT_OF_SCOPE(cma::OnStart(cma::AppType::test));

    for (auto& f : cfgs) fs::remove(f, ec);
    auto root_file = fs::path(GetCfg().getRootYamlPath());
    auto ret = GetCfg().loadAggregated(temporary_name, YamlCacheOp::nothing);
    EXPECT_EQ(ret, LoadCfgStatus::kAllFailed);
    // previous state must be preserved
    EXPECT_FALSE(GetCfg().isBakeryLoaded());
    EXPECT_TRUE(GetCfg().isUserLoaded() ==
                fs::exists(GetCfg().getUserYamlPath(), ec));

    fs::copy_file(root_file, cfgs[0], ec);
    ASSERT_EQ(ec.value(), 0);
    // testing merging
    {
        CreateTestFile(cfgs[1],
                       "global:\n"
                       "  execute: []\n"  // expected clean
                       "  realtime:\n"
                       "    run: a b\n"  // expected array
                       "  sections: \n"
                       "    - x y\n"
                       "    - [z]\n"
                       "  disabled_sections: ~\n");  // no changes

        // prepare and check data
        auto target_config = YAML::LoadFile(cfgs[0].u8string());
        target_config.remove(groups::kPs);
        target_config.remove(groups::kWinPerf);
        target_config.remove(groups::kPlugins);
        target_config.remove(groups::kMrpe);
        target_config.remove(groups::kLocal);
        target_config.remove(groups::kLogFiles);
        target_config.remove(groups::kLogWatchEvent);
        target_config.remove(groups::kFileInfo);

        auto source_bakery = YAML::LoadFile(cfgs[1].u8string());

        // merge bakery to target
        ConfigInfo::smartMerge(target_config, source_bakery,
                               Combine::overwrite);

        // CHECK result
        auto gl = target_config[groups::kGlobal];

        auto sz = gl[vars::kExecute].size();
        ASSERT_EQ(sz, 0);

        auto run_node = gl[vars::kRealTime][vars::kRtRun];
        sz = run_node.size();
        ASSERT_EQ(sz, 0);
        EXPECT_EQ(run_node.as<std::string>(), "a b");
        auto rt = GetInternalArray(gl[vars::kRealTime], vars::kRtRun);
        ASSERT_EQ(rt.size(), 2);
        EXPECT_EQ(rt[0], "a");
        EXPECT_EQ(rt[1], "b");

        auto sections_enabled = GetInternalArray(gl, vars::kSectionsEnabled);
        ASSERT_EQ(sections_enabled.size(), 3);
        EXPECT_EQ(sections_enabled[0], "x");
        EXPECT_EQ(sections_enabled[1], "y");
        EXPECT_EQ(sections_enabled[2], "z");

        // empty node is ignored
        sz = gl[vars::kSectionsDisabled].size();
        ASSERT_EQ(sz, 0);

        auto sections_disabled = GetInternalArray(gl, vars::kSectionsDisabled);
        ASSERT_EQ(sections_disabled.size(), 0);

        std::swap(cfgs[1], cfgs[0]);
        // prepare and check data
        target_config = YAML::LoadFile(cfgs[0].u8string());

        source_bakery = YAML::LoadFile(cfgs[1].u8string());

        // merge and check output INTO core
        ConfigInfo::smartMerge(target_config, source_bakery,
                               Combine::overwrite);

        // CHECK result
        gl = target_config[groups::kGlobal];
        ASSERT_EQ(gl[vars::kExecute].size(), 5);

        run_node = gl[vars::kRealTime][vars::kRtRun];
        ASSERT_EQ(run_node.size(), 3);

        sections_enabled = GetInternalArray(gl, vars::kSectionsEnabled);
        ASSERT_EQ(sections_enabled.size(), 20);

        ASSERT_EQ(gl[vars::kSectionsDisabled].size(), 0);
    }
}

TEST(AgentConfig, Aggregate) {
    namespace fs = std::filesystem;
    std::wstring temporary_name = L"tmp_";
    temporary_name += files::kDefaultMainConfig;
    fs::path cfgs[] = {GetCfg().getRootDir() / temporary_name,
                       GetCfg().getBakeryDir() / temporary_name,
                       GetCfg().getUserDir() / temporary_name};
    cfgs[1].replace_extension("bakery.yml");
    cfgs[2].replace_extension("user.yml");

    std::error_code ec;
    ON_OUT_OF_SCOPE(for (auto& f : cfgs) fs::remove(f, ec););
    ON_OUT_OF_SCOPE(cma::OnStart(cma::AppType::test));

    for (auto& f : cfgs) fs::remove(f, ec);
    auto root_file = fs::path(GetCfg().getRootYamlPath());
    auto ret = GetCfg().loadAggregated(temporary_name, YamlCacheOp::nothing);
    EXPECT_EQ(ret, LoadCfgStatus::kAllFailed);
    // previous state must be preserved
    EXPECT_FALSE(GetCfg().isBakeryLoaded());
    EXPECT_TRUE(GetCfg().isUserLoaded() ==
                fs::exists(GetCfg().getUserYamlPath(), ec));

    fs::copy_file(root_file, cfgs[0], ec);
    ASSERT_EQ(ec.value(), 0);
    // testing merging
    {
        CreateTestFile(
            cfgs[1],
            "bakery:\n"
            "  status: 'loaded'\n"
            "  enabled: true\n"
            "global:\n"
            "  enabled: no\n"
            "  name: 'test name'\n"
            "plugins:\n"
            "  enabled: true\n"
            "  folders:  ['c:\\Users\\Public']\n"  // add
            "  execution:\n"
            "    - pattern: ' $CUSTOM_PLUGINS_PATH$\\windows_updates.vbs'\n"  // add
            "      cache_age: 14400\n"
            "      async: yes\n"
            "      timeout: 600\n"
            "    - pattern: '$BUILTIN_PLUGINS_PATH$\\*.*'\n"  // override
            "      timeout: 31\n"
            "      run: no\n"
            "winperf:\n"
            "  counters:\n"
            "    - 234: if\n"
            "    -  638 : tcp_conn\n"
            "    -   9999 : the_the\n"
            "    - Terminal Services: ts_sessions\n");

        // plugins
        {
            // prepare and check data
            auto core_yaml = YAML::LoadFile(cfgs[0].u8string());
            auto core_plugin = core_yaml[groups::kPlugins];
            ASSERT_EQ(core_plugin[vars::kPluginsExecution].size(), 3);
            ASSERT_EQ(core_plugin[vars::kPluginsFolders].size(), 2);

            auto bakery_yaml = YAML::LoadFile(cfgs[1].u8string());
            auto bakery_plugin = bakery_yaml[groups::kPlugins];
            ASSERT_EQ(bakery_plugin[vars::kPluginsExecution].size(), 2);
            ASSERT_EQ(bakery_plugin[vars::kPluginsFolders].size(), 1);

            // merge and check output INTO BAKERY!
            MergeStringSequence(bakery_plugin, core_plugin,
                                vars::kPluginsFolders);
            MergeMapSequence(bakery_plugin, core_plugin,
                             vars::kPluginsExecution, vars::kPluginPattern);

            // CHECK bakery
            ASSERT_EQ(bakery_plugin[vars::kPluginsFolders].size(), 3);
            ASSERT_EQ(bakery_plugin[vars::kPluginsExecution].size(), 4);
            ASSERT_EQ(bakery_yaml["bakery"]["status"].as<std::string>(),
                      "loaded");
        }

        // winperf
        {
            auto r = YAML::LoadFile(cfgs[0].u8string());
            ASSERT_EQ(r[groups::kWinPerf][vars::kWinPerfCounters].size(), 3);
            auto b = YAML::LoadFile(cfgs[1].u8string());
            ASSERT_EQ(b[groups::kWinPerf][vars::kWinPerfCounters].size(), 4);
            ConfigInfo::smartMerge(r, b, Combine::overwrite);
            ASSERT_EQ(r[groups::kWinPerf][vars::kWinPerfCounters].size(),
                      6);  // three new, 638, 9999 and ts
            ASSERT_EQ(r["bakery"]["status"].as<std::string>(), "loaded");
        }
    }

    ret = GetCfg().loadAggregated(temporary_name, YamlCacheOp::nothing);
    EXPECT_EQ(ret, LoadCfgStatus::kFileLoaded);
    auto yaml = cma::cfg::GetLoadedConfig();
    EXPECT_TRUE(GetCfg().isBakeryLoaded());
    EXPECT_FALSE(GetCfg().isUserLoaded());

    ASSERT_EQ(yaml["bakery"]["status"].as<std::string>(), "loaded");
    auto x = yaml["global"]["enabled"].as<bool>();
    ASSERT_EQ(yaml["global"]["enabled"].as<bool>(), false);
    ASSERT_EQ(yaml["global"]["async"].as<bool>(), true);
    EXPECT_EQ(yaml[groups::kWinPerf][vars::kWinPerfCounters].size(), 6);
    EXPECT_EQ(yaml[groups::kPlugins][vars::kPluginsFolders].size(), 3);
    EXPECT_EQ(yaml[groups::kPlugins][vars::kPluginsExecution].size(), 4);

    CreateTestFile(cfgs[2], "user:\n  status: 'loaded'\nglobal:\n  port: 111");

    ret = GetCfg().loadAggregated(temporary_name, YamlCacheOp::nothing);
    EXPECT_EQ(ret, LoadCfgStatus::kFileLoaded);
    yaml = cma::cfg::GetLoadedConfig();
    ASSERT_EQ(yaml["bakery"]["status"].as<std::string>(), "loaded");
    ASSERT_EQ(yaml["user"]["status"].as<std::string>(), "loaded");
    ASSERT_EQ(yaml["global"]["enabled"].as<bool>(), false);
    ASSERT_EQ(yaml["global"]["port"].as<int>(), 111);
    ASSERT_EQ(yaml["global"]["async"].as<bool>(), true);
    EXPECT_EQ(yaml[groups::kWinPerf][vars::kWinPerfCounters].size(), 6);
    EXPECT_EQ(yaml[groups::kPlugins][vars::kPluginsFolders].size(), 3);
    EXPECT_EQ(yaml[groups::kPlugins][vars::kPluginsExecution].size(), 4);
    EXPECT_TRUE(GetCfg().isBakeryLoaded());
    EXPECT_TRUE(GetCfg().isUserLoaded());
}

TEST(AgentConfig, ReloadWithTimestamp) {
    namespace fs = std::filesystem;
    using namespace std::chrono;
    cma::OnStart(cma::AppType::test);
    ON_OUT_OF_SCOPE(cma::OnStart(cma::AppType::test));
    {
        // prepare file
        auto path = CreateYamlnInTemp("test.yml", "global:\n    ena: yes\n");
        ASSERT_TRUE(!path.empty());
        std::error_code ec;
        ON_OUT_OF_SCOPE(fs::remove(path, ec));

        // load
        auto ret = GetCfg().loadDirect(path);
        auto yaml = GetCfg().getConfig();
        ASSERT_TRUE(yaml.IsMap());
        auto x = yaml["global"];
        ASSERT_NO_THROW(x["ena"].as<bool>(););
        auto val = x["ena"].as<bool>();
        EXPECT_EQ(val, true);

        yaml["global"]["ena"] = false;

        yaml = GetCfg().getConfig();
        val = yaml["global"]["ena"].as<bool>();
        EXPECT_EQ(val, false);

        // file NOT changed, No Load, no changes in the yaml
        ret = GetCfg().loadDirect(path);
        EXPECT_TRUE(ret);
        yaml = GetCfg().getConfig();
        val = yaml["global"]["ena"].as<bool>();
        EXPECT_EQ(val, false);

        // touch file(signal to reload)
        auto ftime = fs::last_write_time(path);
        fs::last_write_time(path, ftime + 1s);

        // file NOT changed, But RELOADED Load, Yaml changed too
        ret = GetCfg().loadDirect(path);
        EXPECT_TRUE(ret);
        yaml = GetCfg().getConfig();
        val = yaml["global"]["ena"].as<bool>();
        EXPECT_EQ(val, true);
    }
}

TEST(AgentConfig, GetValueTest) {
    std::wstring key_path = L"System\\CurrentControlSet\\services\\";
    key_path += L"Ntfs";
    auto type = wtools::GetRegistryValue(key_path, L"Type", 0);
    EXPECT_EQ(type, 2);
    auto group = wtools::GetRegistryValue(key_path, L"Group", L"");
    EXPECT_EQ(group, L"Boot File System");

    type = wtools::GetRegistryValue(key_path, L"Typex", 0);
    EXPECT_EQ(type, 0);
    group = wtools::GetRegistryValue(key_path, L"Groupf", L"--");
    EXPECT_EQ(group, L"--");
}

// #TODO improve this for better coverage
TEST(AgentConfig, FoldersTest) {
    namespace fs = std::filesystem;
    fs::path value = SOLUTION_DIR;
    value /= L"test_files\\work";
    {
        Folders folders;
        auto ret = folders.setRoot(L"", L"");  // good to test

        EXPECT_TRUE(ret);
        EXPECT_TRUE(fs::exists(folders.getRoot()));
        folders.createDataFolderStructure(L"", Folders::CreateMode::with_path);
        EXPECT_TRUE(fs::exists(folders.getData()));
        EXPECT_TRUE(
            folders.getData() ==
            folders.makeDefaultDataFolder(L"", Folders::CreateMode::with_path));
    }  // namespace fs=std::filesystem;

    {
        Folders folders;
        auto ret = folders.setRoot(L"WinDefend", L"");  // good to test
        folders.createDataFolderStructure(L"", Folders::CreateMode::with_path);
        EXPECT_TRUE(ret);
        EXPECT_TRUE(fs::exists(folders.getData()));
        EXPECT_TRUE(fs::exists(folders.getRoot()));
    }

    {
        Folders folders;
        auto ret = folders.setRoot(L"", value.wstring());  // good to test
        folders.createDataFolderStructure(L"", Folders::CreateMode::with_path);
        EXPECT_TRUE(ret);
        EXPECT_TRUE(fs::exists(folders.getData()));
        EXPECT_TRUE(fs::exists(folders.getRoot()));
    }

    {
        Folders folders;
        auto ret =
            folders.setRoot(L"WinDefend", value.wstring());  // good to test
        folders.createDataFolderStructure(L"", Folders::CreateMode::with_path);
        EXPECT_TRUE(ret);
        EXPECT_TRUE(fs::exists(folders.getData()));
        EXPECT_TRUE(fs::exists(folders.getRoot()));
        EXPECT_TRUE(
            folders.getData() ==
            folders.makeDefaultDataFolder(L"", Folders::CreateMode::with_path));
    }
}
}  // namespace cma::cfg::details

namespace cma::cfg {  // to become friendly for cma::cfg classes

TEST(AgentConfig, LogFile) {
    auto fname = cma::cfg::GetCurrentLogFileName();
    EXPECT_TRUE(fname.size() != 0);
}

TEST(AgentConfig, YamlRead) {
    namespace fs = std::filesystem;
    auto file = MakePathToConfigTestFiles(G_SolutionPath) /
                cma::cfg::files::kDefaultDevMinimum;
    auto ret = fs::exists(file);
    ASSERT_TRUE(ret);

    int err = 0;
    auto result = LoadAndCheckYamlFile(file.wstring(), &err);
    auto sz = result.size();
    auto val_global = result["global"];
    auto v = result["globalvas"];
    EXPECT_TRUE(v.size() == 0);
    EXPECT_TRUE(sz > 0);
}

TEST(AgentConfig, InternalArray) {
    const std::string key = "sections";
    auto create_yaml = [key](const std::string& text) -> YAML::Node {
        return YAML::Load(key + ": " + text + "\n");
    };

    {
        auto node = create_yaml("");
        auto result = GetInternalArray(node, key);
        ASSERT_TRUE(result.empty());
    }

    {
        auto node = create_yaml("df ps");
        auto result = GetInternalArray(node, key);
        ASSERT_EQ(result.size(), 2);
        EXPECT_EQ(result[0], "df");
        EXPECT_EQ(result[1], "ps");
    }

    {
        auto node = create_yaml("[df, ps]");
        auto result = GetInternalArray(node, key);
        ASSERT_EQ(result.size(), 2);
        EXPECT_EQ(result[0], "df");
        EXPECT_EQ(result[1], "ps");
    }

    {
        auto node = create_yaml(" \n  - [df, ps]");
        auto result = GetInternalArray(node, key);
        ASSERT_EQ(result.size(), 2);
        EXPECT_EQ(result[0], "df");
        EXPECT_EQ(result[1], "ps");
    }

    {
        auto node = create_yaml(
            " \n  - [df, ps]"
            " \n  - xx");
        auto result = GetInternalArray(node, key);
        ASSERT_EQ(result.size(), 3);
        EXPECT_EQ(result[0], "df");
        EXPECT_EQ(result[1], "ps");
        EXPECT_EQ(result[2], "xx");
    }

    {
        auto node = create_yaml(
            " \n  - [df, ps]"
            " \n  - [xx]");
        auto result = GetInternalArray(node, key);
        ASSERT_EQ(result.size(), 3);
        EXPECT_EQ(result[0], "df");
        EXPECT_EQ(result[1], "ps");
        EXPECT_EQ(result[2], "xx");
    }

    {
        auto node = create_yaml(
            " \n  - [df, ps]"
            " \n  - "
            " \n  - [xx]"
            " \n  - yy zz");
        auto result = GetInternalArray(node, key);
        ASSERT_EQ(result.size(), 5);
        EXPECT_EQ(result[0], "df");
        EXPECT_EQ(result[1], "ps");
        EXPECT_EQ(result[2], "xx");
        EXPECT_EQ(result[3], "yy");
        EXPECT_EQ(result[4], "zz");
    }
}

TEST(AgentConfig, WorkScenario) {
    using namespace std::filesystem;
    using namespace std;
    using namespace cma::cfg;

    vector<wstring> cfg_files;
    cfg_files.emplace_back(files::kDefaultMainConfig);

    auto ret = cma::cfg::InitializeMainConfig(cfg_files, YamlCacheOp::nothing);
    ASSERT_EQ(ret, true);
    auto cfg = cma::cfg::GetLoadedConfig();
    EXPECT_TRUE(cfg.size() >= 1);  // minimum has ONE section

    cfg = cma::cfg::GetLoadedConfig();
    auto sz = cfg.size();
    EXPECT_TRUE(cfg.IsMap());  // minimum has ONE section
    using namespace cma::cfg;

    auto port = GetVal(groups::kGlobal, vars::kPort, -1);
    EXPECT_TRUE(port != -1);

    auto encrypt = GetVal(groups::kGlobal, vars::kGlobalEncrypt, true);
    EXPECT_TRUE(!encrypt);

    auto password =
        GetVal(groups::kGlobal, vars::kGlobalPassword, std::string("ppp"));
    EXPECT_TRUE(password == "secret");

    auto name = GetVal(groups::kGlobal, vars::kName, std::string(""));
    EXPECT_TRUE(name.empty()) << "name should absent";

    auto ipv6 = GetVal(groups::kGlobal, vars::kIpv6, true);
    EXPECT_TRUE(!ipv6);

    auto async = GetVal(groups::kGlobal, vars::kAsync, false);
    EXPECT_TRUE(async);

    auto flush = GetVal(groups::kGlobal, vars::kSectionFlush, true);
    EXPECT_TRUE(flush) << "flush should absent";

    auto execute = GetInternalArray(groups::kGlobal, vars::kExecute);
    EXPECT_TRUE(execute.size() > 3);

    auto only_from = GetInternalArray(groups::kGlobal, vars::kOnlyFrom);
    EXPECT_TRUE(only_from.size() == 0);

#if 0
    // should not supported
    auto host = GetArray<string>(groups::kGlobal, vars::kHost);
    EXPECT_TRUE(host.size() == 1);
#endif

    {
        auto sections_enabled =
            GetInternalArray(groups::kGlobal, vars::kSectionsEnabled);
        EXPECT_EQ(sections_enabled.size(), 20);

        auto sections_disabled =
            GetInternalArray(groups::kGlobal, vars::kSectionsDisabled);
        EXPECT_EQ(sections_disabled.size(), 0) << "no disabled sections";
    }

    {
        auto realtime = GetNode(groups::kGlobal, vars::kRealTime);
        EXPECT_TRUE(realtime.size() == 6);

        auto encrypt = GetVal(realtime, vars::kRtEncrypt, true);
        EXPECT_TRUE(!encrypt);

        auto rt_port = GetVal(realtime, vars::kRtPort, 111);
        EXPECT_EQ(rt_port, cma::cfg::kDefaultRealtimePort);

        auto passphrase =
            GetVal(realtime, vars::kGlobalPassword, std::string());
        EXPECT_TRUE(passphrase == "this is my password");

        auto run = GetInternalArray(realtime, vars::kRtRun);
        EXPECT_TRUE(run.size() == 3);
    }
    {
        auto logging = GetNode(groups::kGlobal, vars::kLogging);
        EXPECT_EQ(logging.size(), 5);

        auto log_location =
            GetVal(logging, vars::kLogLocation, std::string(""));

        EXPECT_TRUE(log_location.empty());

        auto debug = GetVal(logging, vars::kLogDebug, std::string("xxx"));
        EXPECT_TRUE(debug == "yes" || debug == "all");

        auto windbg = GetVal(logging, vars::kLogWinDbg, false);
        EXPECT_TRUE(windbg);

        auto event_log = GetVal(logging, vars::kLogEvent, false);
        EXPECT_TRUE(event_log);

        auto file_log = GetVal(logging, vars::kLogFile, std::string("a.log"));
        EXPECT_TRUE(file_log.empty());
    }

    // winperf
    {
        auto winperf_on = GetVal(groups::kWinPerf, vars::kEnabled, false);
        EXPECT_TRUE(winperf_on);

        auto winperf_counters =
            GetPairArray(groups::kWinPerf, vars::kWinPerfCounters);
        EXPECT_EQ(winperf_counters.size(), 3);
        for (const auto& counter : winperf_counters) {
            auto id = counter.first;
            EXPECT_TRUE(id != "");

            auto name = counter.second;
            EXPECT_TRUE(name != "");
        }
    }

    // mrpe
    {
        auto mrpe_on = GetVal(groups::kMrpe, vars::kEnabled, false);
        EXPECT_TRUE(mrpe_on);

        auto mrpe_timeout = GetVal(groups::kMrpe, vars::kTimeout, 31);
        EXPECT_EQ(mrpe_timeout, 60);
        auto mrpe_parallel = GetVal(groups::kMrpe, vars::kMrpeParallel, true);
        EXPECT_FALSE(mrpe_parallel);
    }

    // system
    {
        auto firewall = GetNode(groups::kSystem, vars::kFirewall);
        auto mode = GetVal(firewall, vars::kFirewallMode, std::string("xx"));
        EXPECT_TRUE(mode == values::kModeConfigure);
    }

    {
        auto mode =
            GetVal(groups::kSystem, vars::kCleanupUninstall, std::string("xx"));
        EXPECT_TRUE(mode == values::kCleanupSmart);
    }

    {
        auto service = GetNode(groups::kSystem, vars::kService);
        auto restart_on_crash = GetVal(service, vars::kRestartOnCrash, false);
        EXPECT_TRUE(restart_on_crash);
        auto error_control =
            GetVal(service, vars::kErrorMode, std::string("bb"));
        EXPECT_EQ(error_control, defaults::kErrorMode);
        auto start_mode = GetVal(service, vars::kStartMode, std::string("aaa"));
        EXPECT_EQ(start_mode, defaults::kStartMode);
    }
}

TEST(AgentConfig, UTF16LE) {
    using namespace std::filesystem;
    using namespace std;
    using namespace cma::cfg;

    // ************************************
    // Typical load scenario
    // ************************************
    auto loader = [](const auto&... Str) -> bool {
        using namespace std;
        using namespace cma::cfg;

        auto cfg_files = cma::tools::ConstructVectorWstring(Str...);

        // loading itself
        auto ret = InitializeMainConfig(cfg_files, YamlCacheOp::nothing);
        if (!ret) return false;

        // verification
        auto cfg = GetLoadedConfig();
        auto sz = cfg.size();
        return cfg.IsMap();  // minimum has ONE section
    };

    details::KillDefaultConfig();

    auto file_utf16 = MakePathToConfigTestFiles(G_SolutionPath) /
                      files::kDefaultDevConfigUTF16;
    bool success = loader(file_utf16.wstring());
    EXPECT_TRUE(success);

    // UNICODE CHECKS
    // This is not right place, but here we have Unicode text in Unicode file
    // we will use possibility to test our conversion functions from wtools
    // #TODO make separate
    auto name_utf8 = GetVal(groups::kGlobal, vars::kName, std::string(""));
    EXPECT_TRUE(name_utf8 != "");
    auto name_utf16 = wtools::ConvertToUTF16(name_utf8);
    EXPECT_TRUE(name_utf16 != L"");
    auto utf8_from_utf16 = wtools::ConvertToUTF8(name_utf16);
    EXPECT_TRUE(utf8_from_utf16 != "");

    EXPECT_TRUE(utf8_from_utf16 == name_utf8);

    cma::OnStart(cma::AppType::test);
}

TEST(AgentConfig, FailScenario_Long) {
    using namespace std::filesystem;
    using namespace std;
    using namespace cma::cfg;

    // ************************************
    // Typical load scenario
    // ************************************
    auto loader = [](auto&... Str) -> bool {
        using namespace std;
        using namespace cma::cfg;

        auto cfg_files = cma::tools::ConstructVectorWstring(Str...);

        // loading itself
        auto ret = InitializeMainConfig(cfg_files, YamlCacheOp::nothing);
        if (!ret) return false;

        // verification
        auto cfg = cma::cfg::GetLoadedConfig();
        cfg = cma::cfg::GetLoadedConfig();
        auto sz = cfg.size();
        return cfg.IsMap();  // minimum has ONE section
    };

    details::KillDefaultConfig();

    bool success = loader(L"StranegName.yml");
    EXPECT_FALSE(success);
    {
        auto port = GetVal(groups::kGlobal, vars::kPort, -1);
        EXPECT_TRUE(port == -1);
    }

    auto test_config_path = MakePathToConfigTestFiles(G_SolutionPath);

    auto file_1 = (test_config_path / files::kDefaultMainConfig).wstring();
    auto file_2 = (test_config_path / files::kDefaultDevMinimum).wstring();

    success = loader(file_1, file_2);
    EXPECT_TRUE(success);

    success =
        loader(L"StrangeName<GTEST>.yml");  // <GTEST> to decrease warning level
                                            // in windows debugger window
    EXPECT_FALSE(success);
    // ************************************

    using namespace cma::cfg;

    auto port = GetVal(groups::kGlobal, vars::kPort, -1);
    EXPECT_EQ(port, -1);
    auto no_bool = GetVal(groups::kGlobal, "xxx", false);
    EXPECT_FALSE(no_bool);
    auto no_int = GetVal(groups::kGlobal, "xxx", 13);
    EXPECT_TRUE(no_int == 13);
    auto no_string = GetVal(groups::kGlobal, "xxx", std::string("string"));
    EXPECT_TRUE(no_string == "string");

    /*
    auto no_wstring = GetVal(groups::kGlobal, "xxx", std::wstring(L"string"));
    EXPECT_TRUE(no_wstring == L"string");
        auto no_array = GetArray<string>(groups::kGlobal, "xxx");
        EXPECT_TRUE(no_array.empty());
    */
    using namespace YAML;
    auto node = GetNode(groups::kGlobal, "xxx2");
    EXPECT_TRUE(node.IsNull() || !node.IsDefined());
    cma::OnStart(cma::AppType::test);
    success = loader(L"StranegName.yml");
    EXPECT_FALSE(success);
}

TEST(AgentConfig, CacheApi) {
    namespace fs = std::filesystem;
    auto name = StoreFileToCache("i am not a file");
    EXPECT_TRUE(name.empty());
    auto source_name = GetCfg().getTempDir() / "test";
    const std::string src("abc");
    auto res = details::CreateTestFile(source_name, src);
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(res, ec););
    auto expected_name = GetCfg().getCacheDir() / source_name.filename();
    fs::remove(expected_name, ec);
    ASSERT_EQ(res.u8string(), source_name.u8string());
    EXPECT_TRUE(fs::exists(res, ec));
    auto x = cma::tools::ReadFileInVector(res);
    ASSERT_TRUE(x.has_value());
    ASSERT_EQ(x->size(), 4);

    EXPECT_TRUE(0 == memcmp(x->data(), (src + "\n").data(), src.size() + 1));
}

TEST(AgentConfig, FunctionalityCheck) {
    namespace fs = std::filesystem;
    using namespace std;
    using namespace cma::cfg;
    using namespace cma::cfg::groups;

    // ************************************
    // Typical load scenario
    // ************************************

    details::KillDefaultConfig();
    EXPECT_NE(global.enabledSections().size(), 0);
    EXPECT_EQ(global.disabledSections().size(), 0);
    details::LoadGlobal();
    EXPECT_TRUE(global.enabledSections().size() == 0);
    EXPECT_TRUE(global.disabledSections().size() == 0);

    // set false parameters
    XLOG::setup::ChangeLogFileName("b.log");
    XLOG::setup::EnableDebugLog(true);
    XLOG::setup::EnableWinDbg(false);
    OnStart(cma::AppType::test);
    auto fname = std::string(XLOG::l.getLogParam().filename());
    EXPECT_TRUE(fname != "b.log");
    fs::path p = fname;
    auto final_name = p.filename();
    EXPECT_TRUE(final_name.u8string() ==
                std::string(cma::cfg::kDefaultLogFileName));

    EXPECT_TRUE(global.enabledSections().size() != 0);
    EXPECT_TRUE(global.disabledSections().size() == 0);

    EXPECT_TRUE(global.realtimePort() == cma::cfg::kDefaultRealtimePort);
    EXPECT_TRUE(global.realtimeTimeout() == cma::cfg::kDefaultRealtimeTimeout);
    EXPECT_FALSE(global.realtimeEncrypt());
    EXPECT_FALSE(global.realtimeEnabled());

    // caching USER
    fs::path source_name = GetCfg().getUserYamlPath();
    fs::path file_to_delete;
    bool delete_required = false;
    if (source_name.empty() ||       // should not happen
        !GetCfg().isUserLoaded()) {  // bad user file
        XLOG::stdio("\nI am generating user yml!\n");
        fs::path user_f = GetCfg().getUserDir();
        user_f /= files::kDefaultMainConfig;
        user_f.replace_extension(files::kDefaultUserExt);
        details::CreateTestFile(
            user_f, "user:\n  status: 'loaded'\nglobal:\n  port: 111");
        delete_required = true;
        file_to_delete = user_f;
    }
    OnStart(AppType::test);
    auto expected_name = GetCfg().getCacheDir() / source_name.filename();
    std::error_code ec;

    {
        std::error_code ec;
        EXPECT_TRUE(fs::exists(expected_name, ec))
            << "no cache made by OnStart";
        fs::remove(expected_name);
        auto ret = cma::cfg::StoreUserYamlToCache();
        EXPECT_TRUE(ret);
        EXPECT_TRUE(fs::exists(expected_name, ec))
            << "no cache made by StoreUserYaml";
    }

    // ************************************
    if (delete_required) {
        fs::remove(file_to_delete, ec);  // clean user folder
        fs::remove(expected_name, ec);   // clean cache folder
    }
    cma::OnStart(cma::AppType::test);
}

TEST(AgentConfig, SectionLoader) {
    using namespace std::filesystem;
    using namespace std;
    using namespace cma::cfg;

    vector<wstring> cfg_files;
    cfg_files.emplace_back(files::kDefaultMainConfig);

    auto ret = cma::cfg::InitializeMainConfig(cfg_files, YamlCacheOp::nothing);
    ASSERT_EQ(ret, true);
    auto cfg = cma::cfg::GetLoadedConfig();
    EXPECT_TRUE(cfg.size() >= 1);  // minimum has ONE section

    Global g;
    g.loadFromMainConfig();
    EXPECT_TRUE(g.enabledInConfig());
    EXPECT_TRUE(g.existInConfig());

    WinPerf w;
    w.loadFromMainConfig();
    EXPECT_TRUE(w.enabledInConfig());
    EXPECT_TRUE(w.existInConfig());

    Plugins p;
    p.loadFromMainConfig(groups::kPlugins);
    EXPECT_NO_THROW(tst::PrintNode(cfg["plugins"], "plugins"));
    EXPECT_TRUE(p.enabledInConfig());
    EXPECT_TRUE(p.existInConfig());
    EXPECT_EQ(p.unitsCount(), 3);
    EXPECT_EQ(p.foldersCount(), 2);

    Plugins p_local;
    p.loadFromMainConfig(groups::kLocal);
    EXPECT_TRUE(p.enabledInConfig());
    EXPECT_TRUE(p.existInConfig());
    EXPECT_EQ(p.unitsCount(), 1);
    EXPECT_TRUE(p.foldersCount() == 1) << "1 Folder is predefined and fixed";
}

TEST(AgentConfig, GlobalTest) {
    namespace fs = std::filesystem;
    using namespace std;
    using namespace cma::cfg;

    Global g;
    g.loadFromMainConfig();
    g.setLogFolder("C:\\Windows\\Logs\\");
    auto fname = g.fullLogFileNameAsString();
    EXPECT_EQ(fname, std::string("C:\\Windows\\Logs\\") + kDefaultLogFileName);

    // empty string is ignored
    g.setLogFolder("");
    fname = g.fullLogFileNameAsString();
    EXPECT_EQ(fname, std::string("C:\\Windows\\Logs\\") + kDefaultLogFileName);

    if (cma::tools::win::IsElevated()) {
        g.setupLogEnvironment();
        fs::path logf = fname;
        fs::remove(logf);
        XLOG::l("TEST WINDOWS LOG");
        XLOG::l("CONTROL SHOT");
        std::error_code ec;
        EXPECT_TRUE(fs::exists(logf, ec));  // check that file is exists

        {
            std::ifstream in(logf.c_str());
            std::stringstream sstr;
            sstr << in.rdbuf();
            auto contents = sstr.str();
            auto n = std::count(contents.begin(), contents.end(), '\n');
            EXPECT_EQ(n, 2);
            EXPECT_NE(std::string::npos, contents.find("TEST WINDOWS LOG"));
            EXPECT_NE(std::string::npos, contents.find("CONTROL SHOT"));
        }
        fs::remove(logf);
    } else {
        xlog::l("skipping write test: program is not elevated");
    }

    fs::path p = GetUserDir();
    g.setLogFolder(p / dirs::kLog);
    g.setupLogEnvironment();
    fname = g.fullLogFileNameAsString();
    std::filesystem::path dir = GetUserDir();
    dir /= dirs::kLog;
    EXPECT_TRUE(
        cma::tools::IsEqual(fname, (dir / kDefaultLogFileName).u8string()));

    EXPECT_TRUE(groups::global.allowedSection("check_mk"));
    EXPECT_TRUE(groups::global.allowedSection("winperf"));
    EXPECT_TRUE(groups::global.allowedSection("uptime"));
    EXPECT_TRUE(groups::global.allowedSection("systemtime"));
    EXPECT_TRUE(groups::global.allowedSection("df"));
    EXPECT_TRUE(groups::global.allowedSection("mem"));
    EXPECT_TRUE(groups::global.allowedSection("services"));

    EXPECT_TRUE(!groups::global.isSectionDisabled("winperf_any"));
    EXPECT_TRUE(!groups::global.allowedSection("_logfiles"));

    auto val = groups::global.getWmiTimeout();
    EXPECT_TRUE((val >= 1) && (val < 100));
}

#define LW_ROOT_APP "- application: warn context"
#define LW_ROOT_STAR "- \"*\": warn nocontext"

#define LW_USER_APP "- application: warn nocontext"
#define LW_USER_SYS "- system: warn context"

static std::string lw_user =
    "  logfile:\n"
    "    " LW_USER_APP
    "\n"
    "    " LW_USER_SYS "\n";

static std::string lw_root =
    "  logfile:\n"
    "    " LW_ROOT_APP
    "\n"
    "    " LW_ROOT_STAR "\n";

TEST(AgentConfig, MergeSeqCombineExpected) {
    EXPECT_EQ(details::GetCombineMode(groups::kWinPerf),
              details::Combine::merge);
    EXPECT_EQ(details::GetCombineMode(groups::kLogWatchEvent),
              details::Combine::merge_value);
    EXPECT_EQ(details::GetCombineMode(""), details::Combine::overwrite);
    EXPECT_EQ(details::GetCombineMode(groups::kLogFiles),
              details::Combine::overwrite);
}

TEST(AgentConfig, MergeSeqCombineValue) {
    YAML::Node user = YAML::Load(lw_user);
    YAML::Node target = YAML::Load(lw_root);
    cma::cfg::details::CombineSequence("name", target["logfile"],
                                       user["logfile"],
                                       details::Combine::merge_value);
    YAML::Emitter emit;
    emit << target["logfile"];
    auto result = emit.c_str();
    auto table = cma::tools::SplitString(result, "\n");
    EXPECT_EQ(table.size(), 3);
    EXPECT_EQ(table[0], LW_USER_APP);
    EXPECT_EQ(table[1], LW_USER_SYS);
    EXPECT_EQ(table[2], LW_ROOT_STAR);
}

TEST(AgentConfig, MergeSeqCombine) {
    YAML::Node user = YAML::Load(lw_user);
    YAML::Node target = YAML::Load(lw_root);
    cma::cfg::details::CombineSequence(
        "name", target["logfile"], user["logfile"], details::Combine::merge);
    YAML::Emitter emit;
    emit << target["logfile"];
    auto result = emit.c_str();
    auto table = cma::tools::SplitString(result, "\n");
    EXPECT_EQ(table.size(), 3);
    EXPECT_EQ(table[0], LW_ROOT_APP);
    EXPECT_EQ(table[1], LW_ROOT_STAR);
    EXPECT_EQ(table[2], LW_USER_SYS);
}

TEST(AgentConfig, MergeSeqOverride) {
    YAML::Node user = YAML::Load(lw_user);
    YAML::Node target = YAML::Load(lw_root);
    cma::cfg::details::CombineSequence("name", target["logfile"],
                                       user["logfile"],
                                       details::Combine::overwrite);
    YAML::Emitter emit;
    emit << target["logfile"];
    auto result = emit.c_str();
    auto table = cma::tools::SplitString(result, "\n");
    EXPECT_EQ(table.size(), 2);
    EXPECT_EQ(table[0], LW_USER_APP);
    EXPECT_EQ(table[1], LW_USER_SYS);
}

static std::string node_text =
    "global:\n"
    "  execute: []\n"  // expected clean
    "  realtime:\n"
    "    run: a b\n"  // expected array
    "  sections:\n"
    "    - x y\n"
    "    - [z]\n"
    "  _sections:\n"
    "    - x y\n"
    "    - [z]\n"
    "  disabled_sections: ~\n"
    "_global:\n"
    "  execute: []\n"  // expected clean
    "  realtime:\n"
    "    run: a b\n"  // expected array
    "  sections: \n"
    "    - x y\n"
    "    - [z]\n"
    "  disabled_sections: ~\n"
    "fileinfo:\n"
    "  execute: []\n"  // expected clean
    "  realtime:\n"
    "    test:\n"  // expected array
    "      _name: 'aaa'\n"
    "  sections:\n"
    "    - x y\n"
    "    - [z]\n"
    "  disabled_sections: ~"

    ;

static std::string node_ok =
    "global:\n"
    "  execute: []\n"  // expected clean
    "  realtime:\n"
    "    run: a b\n"  // expected array
    "  sections:\n"
    "    - x y\n"
    "    - [z]\n"
    "  disabled_sections: ~\n"
    "fileinfo:\n"
    "  execute: []\n"  // expected clean
    "  realtime:\n"
    "    test:\n"  // expected array
    "      {}\n"
    "  sections:\n"
    "    - x y\n"
    "    - [z]\n"
    "  disabled_sections: ~"

    ;

static YAML::Node generateTestNode(const std::string& node_text) {
    try {
        return YAML::Load(node_text);
    } catch (const std::exception& e) {
        XLOG::l("exception '{}'", e.what());
    }

    return {};
}

TEST(AgentConfig, NodeCleanup) {
    ON_OUT_OF_SCOPE(cma::OnStart(AppType::test));
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    {
        const auto node_base = generateTestNode(node_text);
        YAML::Node node = YAML::Clone(node_base);
        ASSERT_TRUE(node.IsMap());
        auto expected_count = RemoveInvalidNodes(node);
        EXPECT_EQ(expected_count, 3);
        YAML::Emitter emit;
        emit << node;
        std::string value = emit.c_str();
        EXPECT_TRUE(!value.empty());

        EXPECT_EQ(value, node_ok);

        expected_count = RemoveInvalidNodes(node);
        EXPECT_EQ(expected_count, 0);
    }
}
static std::string node_plugins_execution =
    "plugins:\n"
    "  execution:\n"  // expected clean
    "  - pattern: a_1\n"
    "    async: yes\n"
    "    cache_age: 1\n"
    "    run: yes\n"  // expected array
    "  - pattern: a_0\n"
    "    async: yes\n"
    "    run: yes\n"  // expected array
    "  - pattern: a_2600\n"
    "    async: yes\n"
    "    cache_age: 2600\n"
    "    run: yes\n"  // expected array
    "  - pattern: s_eq_a_2600\n"
    "    cache_age: 2600\n"
    "  - pattern: s_2\n"
    "    cache_age: 0\n"
    "    retry_count: 1\n"
    "    run: no\n"

    ;

TEST(AgentConfig, PluginsExecutionParams) {
    ON_OUT_OF_SCOPE(cma::OnStart(AppType::test));
    {
        const auto node_base = generateTestNode(node_plugins_execution);
        auto node = YAML::Clone(node_base);
        ASSERT_TRUE(node.IsMap());
        auto node_plugins = node["plugins"];
        ASSERT_TRUE(node.IsMap());
        ASSERT_TRUE(node_plugins[vars::kPluginsExecution].IsSequence());

        auto units =
            GetArray<YAML::Node>(node_plugins[vars::kPluginsExecution]);

        std::vector<Plugins::ExeUnit> exe_units;
        LoadExeUnitsFromYaml(exe_units, units);
        EXPECT_EQ(exe_units.size(), 5);

        EXPECT_EQ(exe_units[0].pattern(), "a_1");
        EXPECT_EQ(exe_units[0].cacheAge(), kMinimumCacheAge);
        EXPECT_EQ(exe_units[0].async(), true);
        for (auto e : exe_units) {
            EXPECT_TRUE(e.source().IsMap());
            EXPECT_TRUE(e.sourceText().empty());
        }

        EXPECT_EQ(exe_units[1].pattern(), "a_0");
        EXPECT_EQ(exe_units[1].cacheAge(), 0);
        EXPECT_EQ(exe_units[1].async(), true);

        EXPECT_EQ(exe_units[2].pattern(), "a_2600");
        EXPECT_EQ(exe_units[2].cacheAge(), 2600);
        EXPECT_EQ(exe_units[2].async(), true);
        for (int i = 0; i < 4; i++) {
            EXPECT_TRUE(exe_units[2].run());
            EXPECT_EQ(exe_units[2].retry(), 0);
        }

        EXPECT_EQ(exe_units[3].pattern(), "s_eq_a_2600");
        EXPECT_EQ(exe_units[3].cacheAge(), 2600);
        EXPECT_EQ(exe_units[3].async(), true);

        EXPECT_EQ(exe_units[4].pattern(), "s_2");
        EXPECT_EQ(exe_units[4].run(), false);
        EXPECT_EQ(exe_units[4].retry(), 1);
    }
}

TEST(AgentConfig, ApplyValueIfScalar) {
    auto e = YAML::Load(
        "pattern: '*'\n"
        "run: no\n"
        "async: yes\n"
        "cache_age: 193\n"
        "timeout: 77\n"
        "retry_count: 7\n");
    auto e_ = YAML::Load(
        "pattern: '*'\n"
        "_run: no\n"
        "_async: yes\n"
        "_cache_age: 193\n"
        "_timeout: 77\n"
        "_retry_count: 7\n");
    bool run = true;
    bool async = false;
    int cache_age = 0;
    int timeout = cma::cfg::kDefaultPluginTimeout;
    int retry = 0;
    EXPECT_NO_THROW(ApplyValueIfScalar(YAML::Node(), run, ""));
    EXPECT_NO_THROW(ApplyValueIfScalar(e, run, ""));
    EXPECT_TRUE(run);

    // values should not be changed here
    EXPECT_NO_THROW(ApplyValueIfScalar(e_, run, vars::kPluginRun));
    EXPECT_TRUE(run);
    EXPECT_NO_THROW(ApplyValueIfScalar(e_, async, vars::kPluginAsync));
    EXPECT_FALSE(async);
    EXPECT_NO_THROW(ApplyValueIfScalar(e_, retry, vars::kPluginRetry));
    EXPECT_EQ(retry, 0);
    EXPECT_NO_THROW(ApplyValueIfScalar(e_, timeout, vars::kPluginTimeout));
    EXPECT_EQ(timeout, cma::cfg::kDefaultPluginTimeout);
    EXPECT_NO_THROW(ApplyValueIfScalar(e_, cache_age, vars::kPluginCacheAge));
    EXPECT_EQ(cache_age, 0);

    // values should BE changed here
    tst::PrintNode(e, "a");
    EXPECT_NO_THROW(ApplyValueIfScalar(e, run, vars::kPluginRun));
    EXPECT_FALSE(run);
    EXPECT_NO_THROW(ApplyValueIfScalar(e, async, vars::kPluginAsync));
    EXPECT_TRUE(async);
    EXPECT_NO_THROW(ApplyValueIfScalar(e, retry, vars::kPluginRetry));
    EXPECT_EQ(retry, 7);
    EXPECT_NO_THROW(ApplyValueIfScalar(e, timeout, vars::kPluginTimeout));
    EXPECT_EQ(timeout, 77);
    EXPECT_NO_THROW(ApplyValueIfScalar(e, cache_age, vars::kPluginCacheAge));
    EXPECT_EQ(cache_age, 193);
}

TEST(AgentConfig, ExeUnitTest) {
    Plugins::ExeUnit e;
    Plugins::ExeUnit e2;
    EXPECT_EQ(e.async(), false);
    EXPECT_EQ(e.run(), true);
    EXPECT_EQ(e.timeout(), cma::cfg::kDefaultPluginTimeout);
    EXPECT_EQ(e.cacheAge(), 0);
    EXPECT_EQ(e.retry(), 0);
    EXPECT_TRUE(e.group().empty());
    EXPECT_TRUE(e.user().empty());

    e.async_ = true;
    e.run_ = false;
    e.group_ = "g";
    e.user_ = "u u";

    e.timeout_ = 1;
    e.cache_age_ = 1111;
    e.retry_ = 3;
    EXPECT_EQ(e.async(), true);
    EXPECT_EQ(e.run(), false);
    EXPECT_EQ(e.timeout(), 1);
    EXPECT_EQ(e.cacheAge(), 1111);
    EXPECT_EQ(e.retry(), 3);

    EXPECT_EQ(e.group(), "g");
    EXPECT_EQ(e.user(), "u u");

    e.resetConfig();
    EXPECT_EQ(e.async(), false);
    EXPECT_EQ(e.run(), true);
    EXPECT_EQ(e.timeout(), cma::cfg::kDefaultPluginTimeout);
    EXPECT_EQ(e.cacheAge(), 0);
    EXPECT_EQ(e.retry(), 0);

    EXPECT_TRUE(e.group().empty());
    EXPECT_TRUE(e.user().empty());
}

TEST(AgentConfig, ExeUnitTestYaml) {
    using namespace cma::cfg;

    std::vector<Plugins::ExeUnit> exe_units;
    auto execution_yaml = YAML::Load(
        "execution:\n"
        "- pattern     : '1'\n"
        "  timeout     : 1\n"
        "  run         : yes\n"
        "\n"
        "- pattern     : '2'\n"
        "  timeout     : 2\n"
        "  run         : no\n"
        "\n"
        "- pattern     : '3'\n"
        "  group       : Users\n"
        "\n"
        "- pattern     : '4'\n"
        "  retry_count : 4\n"
        "  user        : users_\n"
        "\n"
        "- pattern     : '5'\n"
        "  run         : false\n"
        "  async       : true\n"
        "  cache_age   : 5\n"
        "  group       : 'a a a '\n"
        "\n"

    );
    XLOG::l.t() << execution_yaml;
    auto yaml_units =
        GetArray<YAML::Node>(execution_yaml, vars::kPluginsExecution);
    LoadExeUnitsFromYaml(exe_units, yaml_units);
    ASSERT_EQ(exe_units.size(), 5);

    struct Data {
        std::string p;
        bool async;
        bool run;
        int timeout;
        int cache_age;
        int retry;
        std::string group;
        std::string user;
    } data[5] = {
        {"1", false, true, 1, 0, 0, "", ""},
        {"2", false, false, 2, 0, 0, "", ""},
        {"3", false, true, kDefaultPluginTimeout, 0, 0, "Users", ""},
        {"4", false, true, kDefaultPluginTimeout, 0, 4, "", "users_"},
        {"5", true, false, kDefaultPluginTimeout, 120, 0, "a a a ", ""},
    };

    int i = 0;
    for (const auto& d : data) {
        EXPECT_EQ(exe_units[i].pattern(), d.p);
        EXPECT_EQ(exe_units[i].async(), d.async);
        EXPECT_EQ(exe_units[i].run(), d.run);
        EXPECT_EQ(exe_units[i].timeout(), d.timeout);
        EXPECT_EQ(exe_units[i].cacheAge(), d.cache_age);
        EXPECT_EQ(exe_units[i].retry(), d.retry);
        EXPECT_EQ(exe_units[i].group(), d.group);
        EXPECT_EQ(exe_units[i].user(), d.user);
        ++i;
    }
}

#if 0
TEST(AgentConfig, LoadUtf8) {
    // disabled code to check how valid is unicode files
    cma::OnStart(AppType::test);
    std::filesystem::path d = GetCfg().getUserDir().u8string();
    auto load = YAML::LoadFile((d / "test_utf8.escaped.yml").u8string());
    //auto load = YAML::LoadFile((d / "test_utf8.unicode.yml").u8string());
    EXPECT_TRUE(load.size() > 0);
    YAML::Emitter e;
    e << load;
    std::cout << e.c_str();
    auto z = e.c_str();
    std::filesystem::path n = d / "test.yml";
    std::ofstream ofs(n.u8string());

    ofs << z << " \n";
}
#endif

static void SetCfgMode(YAML::Node cfg, std::string_view name,
                       std::string_view mode) {
    using namespace cma::cfg;
    cfg[groups::kSystem] = YAML::Load(fmt::format("{}: {}\n", name, mode));
}

TEST(AgentConfig, CleanupUninstall) {
    using namespace cma::cfg;
    OnStartTest();
    ON_OUT_OF_SCOPE(OnStartTest());
    auto cfg = cma::cfg::GetLoadedConfig();
    constexpr std::wstring_view app_name = L"test.exe.exe";

    // remove all from the Firewall
    std::pair<std::string_view, details::CleanMode> fixtures[] = {
        {values::kCleanupNone, details::CleanMode::none},
        {values::kCleanupSmart, details::CleanMode::smart},
        {values::kCleanupAll, details::CleanMode::all}};

    for (auto& [n, v] : fixtures) {
        SetCfgMode(cfg, vars::kCleanupUninstall, n);
        EXPECT_EQ(details::GetCleanDataFolderMode(), v);
    }
}
}  // namespace cma::cfg
