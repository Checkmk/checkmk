// test-upgrade.cpp

// complicated things LWA -> NWA

#include "pch.h"

#include <filesystem>

#include "cap.h"
#include "cfg.h"
#include "read_file.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"
#include "upgrade.h"

namespace fs = std::filesystem;

namespace cma::cfg::upgrade {

extern std::filesystem::path G_LegacyAgentPresetPath;
void SetLegacyAgentPath(const std::filesystem::path &path);

const std::string ini_expected = "b53c5b77c595ba7e";
const std::string ini_name = "check_mk.hash.ini";

const std::string state_expected = "a71dfa65aacb1b52";
const std::string state_name = "cmk-update-agent.state";

const std::string new_expected = "13dd8be2f9ad5894";
const std::string dat_name = "checkmk.hash.dat";
const std::string dat_defa_name = "checkmk.defa.hash.dat";

TEST(UpgradeTest, GetHash) {
    auto ini = tst::MakePathToUnitTestFiles() / ini_name;
    auto state = tst::MakePathToUnitTestFiles() / state_name;
    EXPECT_EQ(GetOldHashFromFile(ini, kIniHashMarker), ini_expected);
    EXPECT_EQ(GetOldHashFromFile(state, kStateHashMarker), state_expected);

    EXPECT_EQ(GetOldHashFromIni(ini), ini_expected);
    EXPECT_EQ(GetOldHashFromState(state), state_expected);
}

TEST(UpgradeTest, GetDefaHash) {
    auto dat = tst::MakePathToUnitTestFiles() / dat_defa_name;
    auto new_hash = GetNewHash(dat);
    EXPECT_TRUE(new_hash.empty());
    EXPECT_NO_THROW(GetNewHash("<GTEST>"));
    auto new_weird_hash = GetNewHash("<GTEST>");
    EXPECT_TRUE(new_weird_hash.empty());
}

TEST(UpgradeTest, PatchOldFilesWithDatHash) {
    ASSERT_TRUE(G_LegacyAgentPresetPath.empty());

    tst::TempFolder tmp("PatchOldFilesWithDatHash");
    SetLegacyAgentPath(tmp.path());
    ON_OUT_OF_SCOPE(SetLegacyAgentPath(""););

    auto state_dir = tmp.path() / dirs::kAuStateLocation;
    fs::create_directories(state_dir);
    fs::path dir = tst::MakePathToUnitTestFiles();
    auto ini = dir / ini_name;
    fs::copy_file(ini, tmp.path() / files::kIniFile);
    auto state = dir / state_name;
    fs::copy_file(state,
                  tmp.path() / dirs::kAuStateLocation / files::kAuStateFile);

    auto expected_dat_file = ConstructDatFileName();
    fs::create_directories(expected_dat_file.parent_path());
    // create file
    fs::copy_file(tst::MakePathToUnitTestFiles() / dat_name, expected_dat_file);

    ASSERT_TRUE(PatchOldFilesWithDatHash());

    auto state_hash = GetOldHashFromState(tmp.path() / dirs::kAuStateLocation /
                                          files::kAuStateFile);
    EXPECT_EQ(state_hash, new_expected);

    auto ini_hash = GetOldHashFromIni(tmp.path() / files::kIniFile);
    EXPECT_EQ(ini_hash, new_expected);
}

TEST(UpgradeTest, PatchIniHash) {
    auto ini = tst::MakePathToUnitTestFiles() / ini_name;
    auto old_hash = GetOldHashFromIni(ini);
    ASSERT_TRUE(!old_hash.empty());
    EXPECT_EQ(old_hash, ini_expected);

    auto dat = tst::MakePathToUnitTestFiles() / dat_name;
    auto new_hash = GetNewHash(dat);
    ASSERT_TRUE(!new_hash.empty());
    EXPECT_EQ(new_hash, new_expected);

    tst::TempFolder tmp("PatchIniHash");

    fs::copy_file(ini, tmp.path() / ini_name);
    fs::copy_file(dat, tmp.path() / dat_name);

    EXPECT_TRUE(PatchIniHash(tmp.path() / ini_name, new_hash));

    old_hash = GetOldHashFromIni(tmp.path() / ini_name);
    EXPECT_EQ(old_hash, new_expected);
}
TEST(UpgradeTest, PatchStateHash) {
    auto state = tst::MakePathToUnitTestFiles() / state_name;
    auto old_hash = GetOldHashFromState(state);
    ASSERT_TRUE(!old_hash.empty());
    EXPECT_EQ(old_hash, state_expected);

    auto dat = tst::MakePathToUnitTestFiles() / dat_name;
    auto new_hash = GetNewHash(dat);
    ASSERT_TRUE(!new_hash.empty());
    EXPECT_EQ(new_hash, new_expected);

    tst::TempFolder tmp("PatchStateHash");

    fs::copy_file(state, tmp.path() / state_name);
    fs::copy_file(dat, tmp.path() / dat_name);
    EXPECT_TRUE(PatchStateHash(tmp.path() / state_name, new_hash));

    old_hash = GetOldHashFromState(tmp.path() / state_name);
    EXPECT_TRUE(!old_hash.empty());
    EXPECT_EQ(old_hash, new_expected);
}

std::string nullfile = "";
std::string not_bakeryfile_strange =
    "[local]\n"
    "# define maximum cache age for scripts matching specified patterns - first match wins\n"
    "cache_age a* = 900\n";

std::string bakeryfile =
    "# Created by Check_MK Agent Bakery.\n"
    "# This file is managed via WATO, do not edit manually or you \n"
    "# lose your changes next time when you update the agent.\n"
    "\n"
    "[global]\n"
    "    # TCP port the agent is listening on\n"
    "    port = 6556\n"
    "\n"
    "    # Create logfiles useful for tracing crashes of the agent\n"
    "    # crash_debug = yes\n"
    "    # Create logfiles useful for tracing crashes of the agent\n"
    "    logging = all\n"
    "\n"
    "\n"
    "[local]\n"
    "# define maximum cache age for scripts matching specified patterns - first match wins\n"
    "cache_age a* = 900\n"
    "\n"
    "# define timeouts for scripts matching specified patterns - first match wins\n"
    "\n"
    "\n"
    "[plugins]\n"
    "# define maximum cache age for scripts matching specified patterns - first match wins\n"
    "cache_age b* = 1560\n"
    "\n"
    "# define timeouts for scripts matching specified patterns - first match wins\n"
    "timeout * = 97\n"
    "\n"
    "\n"
    "[winperf]\n"
    "    counters = Terminal Services:ts_sessions\n"
    "\n";

std::string not_bakeryfile =
    "# Created by Check_MK Agent B kery.\n"
    "# This file is managed via WATO, do not edit manually or you \n"
    "# lose your changes next time when you update the agent.\n"
    "\n"
    "[global]\n"
    "    # TCP port the agent is listening on\n"
    "    port = 6556\n"
    "\n"
    "    # Create logfiles useful for tracing crashes of the agent\n"
    "    crash_debug = yes\n"
    "\n"
    "\n"
    "[local]\n"
    "# define maximum cache age for scripts matching specified patterns - first match wins\n"
    "cache_age a* = 900\n"
    "\n"
    "# define timeouts for scripts matching specified patterns - first match wins\n"
    "\n"
    "\n"
    "[plugins]\n"
    "# define maximum cache age for scripts matching specified patterns - first match wins\n"
    "cache_age b* = 1560\n"
    "\n"
    "# define timeouts for scripts matching specified patterns - first match wins\n"
    "timeout * = 97\n"
    "\n"
    "\n"
    "[winperf]\n"
    "    counters = Terminal Services:ts_sessions\n"
    "\n";

static void CreateFileTest(std::filesystem::path Path, std::string Content) {
    std::ofstream ofs(Path);

    ofs << Content;
}

static auto CreateIniFile(std::filesystem::path Lwa, const std::string Content,
                          const std::string YamlName) {
    auto ini_file = Lwa / (YamlName + ".ini");
    CreateFileTest(Lwa / ini_file, Content);
    return ini_file;
}

static std::tuple<std::filesystem::path, std::filesystem::path> CreateInOut() {
    namespace fs = std::filesystem;
    fs::path temp_dir = cma::cfg::GetTempDir();
    auto normal_dir =
        temp_dir.wstring().find(L"\\tmp", 0) != std::wstring::npos;
    if (normal_dir) {
        std::error_code ec;
        auto lwa_dir = temp_dir / "in";
        auto pd_dir = temp_dir / "out";
        fs::create_directories(lwa_dir, ec);
        fs::create_directories(pd_dir, ec);
        return {lwa_dir, pd_dir};
    }
    return {};
}

TEST(UpgradeTest, CheckProtocolUpdate) {
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    auto [old_location, new_location] = CreateInOut();
    EXPECT_TRUE(
        UpdateProtocolFile(new_location.wstring(), old_location.wstring()));
    EXPECT_FALSE(
        UpdateProtocolFile(new_location.wstring(), new_location.wstring()));

    std::error_code ec;
    auto old_file = ConstructProtocolFileName(old_location);
    EXPECT_EQ(
        old_location.string() + "\\" + std::string(files::kUpgradeProtocol),
        old_file.string());

    auto x = CreateProtocolFile(old_location, "  old_file");
    ASSERT_TRUE(fs::exists(old_file, ec));

    EXPECT_TRUE(
        UpdateProtocolFile(new_location.wstring(), old_location.wstring()));
    auto new_file = ConstructProtocolFileName(new_location);
    EXPECT_TRUE(fs::exists(new_file, ec));
    EXPECT_FALSE(fs::exists(old_file, ec));
    auto content = cma::tools::ReadFileInString(new_file.string().c_str());
    ASSERT_TRUE(content.has_value());
    EXPECT_TRUE(content->find("old_file") != std::string::npos);

    x = CreateProtocolFile(old_location, "  new_file");
    EXPECT_TRUE(
        UpdateProtocolFile(new_location.wstring(), old_location.wstring()));
    EXPECT_TRUE(fs::exists(new_file, ec));
    EXPECT_FALSE(fs::exists(old_file, ec));
    content = cma::tools::ReadFileInString(new_file.string().c_str());
    ASSERT_TRUE(content.has_value());
    EXPECT_TRUE(content->find("old_file") != std::string::npos);
}

TEST(UpgradeTest, CreateProtocol) {
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    namespace fs = std::filesystem;
    fs::path dir = cma::cfg::GetTempDir();
    auto x = CreateProtocolFile(dir, "  aaa: aaa");
    ASSERT_TRUE(x);

    auto protocol_file = ConstructProtocolFileName(dir);
    auto f = cma::tools::ReadFileInVector(protocol_file);
    ASSERT_TRUE(f.has_value());
    auto file_content = f.value();
    std::string str((const char *)file_content.data(), file_content.size());
    auto table = cma::tools::SplitString(str, "\n");
    EXPECT_EQ(table.size(), 3);
}

static std::string for_patch =
    "plugins:\n"
    "  execution:\n"
    "    - pattern: 'test1'\n"
    "      timeout: 60\n"
    "      run: yes\n"
    "    - pattern: 'a\\test2'\n"
    "      timeout: 60\n"
    "      run: no\n"
    "    - pattern: '\\test2'\n"
    "      timeout: 60\n"
    "      run: no\n"
    "    - pattern: '/test3'\n"
    "      timeout: 60\n"
    "      run: no\n"
    //
    ;

TEST(UpgradeTest, PatchRelativePath) {
    auto yaml = YAML::Load(for_patch);
    EXPECT_FALSE(PatchRelativePath(
        yaml, groups::kLocal, vars::kPluginsExecution, vars::kPluginPattern,
        cma::cfg::vars::kPluginUserFolder));
    EXPECT_FALSE(PatchRelativePath(
        yaml, groups::kPlugins, vars::kPluginAsyncStart, vars::kPluginPattern,
        cma::cfg::vars::kPluginUserFolder));
    EXPECT_TRUE(PatchRelativePath(yaml, groups::kPlugins,
                                  vars::kPluginsExecution, vars::kPluginRetry,
                                  cma::cfg::vars::kPluginUserFolder))
        << "invalid subkey is allowed";

    ASSERT_TRUE(PatchRelativePath(yaml, groups::kPlugins,
                                  vars::kPluginsExecution, vars::kPluginPattern,
                                  cma::cfg::vars::kPluginUserFolder));
    auto seq = yaml[groups::kPlugins][vars::kPluginsExecution];
    ASSERT_TRUE(seq.IsSequence());
    ASSERT_EQ(seq.size(), 4);

    EXPECT_EQ(seq[0][vars::kPluginPattern].as<std::string>(),
              std::string(cma::cfg::vars::kPluginUserFolder) + "\\test1");
    EXPECT_EQ(seq[1][vars::kPluginPattern].as<std::string>(),
              std::string(cma::cfg::vars::kPluginUserFolder) + "\\a\\test2");
    EXPECT_EQ(seq[2][vars::kPluginPattern].as<std::string>(), "\\test2");
    EXPECT_EQ(seq[3][vars::kPluginPattern].as<std::string>(), "/test3");

    ASSERT_TRUE(PatchRelativePath(yaml, groups::kPlugins,
                                  vars::kPluginsExecution, vars::kPluginPattern,
                                  cma::cfg::vars::kPluginUserFolder));
    seq = yaml[groups::kPlugins][vars::kPluginsExecution];
    ASSERT_TRUE(seq.IsSequence());
    ASSERT_EQ(seq.size(), 4);

    EXPECT_EQ(seq[0][vars::kPluginPattern].as<std::string>(),
              std::string(cma::cfg::vars::kPluginUserFolder) + "\\test1");
    EXPECT_EQ(seq[1][vars::kPluginPattern].as<std::string>(),
              std::string(cma::cfg::vars::kPluginUserFolder) + "\\a\\test2");
    EXPECT_EQ(seq[2][vars::kPluginPattern].as<std::string>(), "\\test2");
    EXPECT_EQ(seq[3][vars::kPluginPattern].as<std::string>(), "/test3");
}

std::filesystem::path ConstructBakeryYmlPath(std::filesystem::path pd_dir) {
    auto bakery_yaml = pd_dir / dirs::kBakery / files::kDefaultMainConfigName;
    bakery_yaml += files::kDefaultBakeryExt;
    return bakery_yaml;
}

std::filesystem::path ConstructUserYmlPath(std::filesystem::path pd_dir) {
    auto user_yaml = pd_dir / files::kDefaultMainConfigName;
    user_yaml += files::kDefaultUserExt;
    return user_yaml;
}

TEST(UpgradeTest, LoggingSupport) {
    cma::OnStartTest();
    auto temp_fs{tst::TempCfgFs::Create()};

    fs::path install_yml{fs::path(dirs::kFileInstallDir) /
                         files::kInstallYmlFileW};

    // without
    ASSERT_TRUE(temp_fs->createRootFile(
        install_yml, "# Packaged\nglobal:\n  enabled: yes\n  install: no"));

    auto [lwa_dir, pd_dir] = CreateInOut();
    ASSERT_TRUE(!lwa_dir.empty() && !pd_dir.empty());

    std::error_code ec;

    auto expected_bakery_name = ConstructBakeryYmlPath(pd_dir);
    auto expected_user_name = ConstructUserYmlPath(pd_dir);

    // bakery file and no local
    {
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto name = "check_mk";
        auto ini = CreateIniFile(lwa_dir, bakeryfile, name);
        EXPECT_TRUE(IsBakeryIni(ini));
        auto yaml_file = CreateBakeryYamlFromIni(ini, pd_dir, name);
        EXPECT_EQ(yaml_file.filename().wstring(),
                  wtools::ConvertToUTF16(name) + files::kDefaultBakeryExt);
        auto yaml = YAML::LoadFile(yaml_file.u8string());
        EXPECT_TRUE(yaml.IsMap());
        auto yml_global = yaml[groups::kGlobal];
        ASSERT_TRUE(yml_global.IsMap());
        auto logging = cma::cfg::GetNode(yml_global, vars::kLogging);
        ASSERT_TRUE(logging.IsMap());

        auto debug =
            cma::cfg::GetVal(logging, vars::kLogDebug, std::string(""));

        EXPECT_EQ(logging[vars::kLogDebug].as<std::string>(), "all");
    }
}

TEST(UpgradeTest, UserIniPackagedAgent) {
    cma::OnStartTest();
    auto temp_fs{tst::TempCfgFs::Create()};

    fs::path install_yml{fs::path(dirs::kFileInstallDir) /
                         files::kInstallYmlFileW};
    ASSERT_TRUE(temp_fs->createRootFile(
        install_yml, "# Packaged\nglobal:\n  enabled: yes\n  install: no"));

    auto [lwa_dir, pd_dir] = CreateInOut();
    ASSERT_TRUE(!lwa_dir.empty() && !pd_dir.empty());

    std::error_code ec;

    auto expected_bakery_name = ConstructBakeryYmlPath(pd_dir);
    auto expected_user_name = ConstructUserYmlPath(pd_dir);

    // bakery file and no local
    {
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto name = "check_mk";
        auto ini = CreateIniFile(lwa_dir, bakeryfile, name);
        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_FALSE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        EXPECT_TRUE(user_exists);
        EXPECT_TRUE(fs::exists(expected_bakery_name, ec));
        EXPECT_FALSE(fs::exists(expected_user_name, ec));
    }

    // bakery file and local
    {
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto u_name = "check_mk";
        CreateIniFile(lwa_dir, bakeryfile, u_name);
        auto l_name = "check_mk_local";
        CreateIniFile(lwa_dir, not_bakeryfile_strange, l_name);

        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_TRUE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        EXPECT_TRUE(user_exists);
        EXPECT_TRUE(fs::exists(expected_bakery_name, ec));
        EXPECT_TRUE(fs::exists(expected_user_name, ec));
        auto bakery_size = fs::file_size(expected_bakery_name, ec);
        auto user_size = fs::file_size(expected_user_name, ec);
        EXPECT_TRUE(bakery_size > user_size);
    }

    // private file and no local
    {
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto name = "check_mk";
        auto ini = CreateIniFile(lwa_dir, not_bakeryfile, name);
        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_FALSE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        EXPECT_TRUE(user_exists);
        EXPECT_TRUE(fs::exists(expected_user_name, ec));
        EXPECT_FALSE(fs::exists(expected_bakery_name, ec));
    }

    // private file and local
    {
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto u_name = "check_mk";
        CreateIniFile(lwa_dir, not_bakeryfile, u_name);
        auto l_name = "check_mk_local";
        CreateIniFile(lwa_dir, not_bakeryfile_strange, l_name);

        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_TRUE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        EXPECT_TRUE(user_exists);
        EXPECT_TRUE(fs::exists(expected_bakery_name, ec));
        EXPECT_TRUE(fs::exists(expected_user_name, ec));
        auto bakery_size = fs::file_size(expected_bakery_name, ec);
        auto user_size = fs::file_size(expected_user_name, ec);
        EXPECT_TRUE(bakery_size > user_size);
    }

    // null file + local
    {
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto u_name = "check_mk";
        CreateIniFile(lwa_dir, nullfile, u_name);
        auto l_name = "check_mk_local";
        CreateIniFile(lwa_dir, not_bakeryfile_strange, l_name);

        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_TRUE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        EXPECT_FALSE(user_exists);
        EXPECT_FALSE(fs::exists(expected_bakery_name, ec));
        EXPECT_TRUE(fs::exists(expected_user_name, ec));
    }

    // no file + local
    {
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto l_name = "check_mk_local";
        CreateIniFile(lwa_dir, not_bakeryfile_strange, l_name);

        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_TRUE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        EXPECT_FALSE(user_exists);
        EXPECT_FALSE(fs::exists(expected_bakery_name, ec));
        EXPECT_TRUE(fs::exists(expected_user_name, ec));
    }
}

void SimulateWatoInstall(const std::filesystem::path &lwa,
                         const std::filesystem::path &pd_dir) {
    auto bakery_yaml = ConstructBakeryYmlPath(pd_dir);
    auto user_yaml = ConstructUserYmlPath(pd_dir);
    std::error_code ec;
    fs::create_directory(pd_dir / dirs::kBakery, ec);
    ASSERT_EQ(ec.value(), 0);
    tst::CreateTextFile(bakery_yaml, "11");
    tst::CreateTextFile(user_yaml, "0");
}

TEST(UpgradeTest, UserIniWatoAgent) {
    // make temporary filesystem
    auto temp_fs{tst::TempCfgFs::Create()};
    // simulate WATO installation
    fs::path install_yml{fs::path(dirs::kFileInstallDir) /
                         files::kInstallYmlFileW};
    ASSERT_TRUE(temp_fs->createRootFile(install_yml, "# Doesn't matter"));

    auto [lwa_dir, pd_dir] = CreateInOut();

    ASSERT_TRUE(!lwa_dir.empty() && !pd_dir.empty());

    std::error_code ec;

    // SIMULATE wato agent installation
    auto bakery_yaml = ConstructBakeryYmlPath(pd_dir);
    auto user_yaml = ConstructUserYmlPath(pd_dir);

    // bakery file and no local
    {
        SimulateWatoInstall(lwa_dir, pd_dir);
        ASSERT_EQ(DetermineInstallationType(), InstallationType::wato);
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto name = "check_mk";
        auto ini = CreateIniFile(lwa_dir, bakeryfile, name);
        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_FALSE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        EXPECT_FALSE(user_exists);
        // no changes
        EXPECT_EQ(fs::file_size(bakery_yaml, ec), 2);
        EXPECT_EQ(fs::file_size(user_yaml, ec), 1);
    }

    // bakery file and local
    {
        SimulateWatoInstall(lwa_dir, pd_dir);
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto u_name = "check_mk";
        CreateIniFile(lwa_dir, bakeryfile, u_name);
        auto l_name = "check_mk_local";
        CreateIniFile(lwa_dir, not_bakeryfile_strange, l_name);

        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_TRUE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        EXPECT_FALSE(user_exists);
        // local changed
        EXPECT_EQ(fs::file_size(bakery_yaml, ec), 2);
        EXPECT_GE(fs::file_size(user_yaml, ec), 50);
    }

    // private file and no local
    {
        SimulateWatoInstall(lwa_dir, pd_dir);
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto name = "check_mk";
        auto ini = CreateIniFile(lwa_dir, not_bakeryfile, name);
        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_FALSE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);

        EXPECT_FALSE(user_exists);
        // no changes
        EXPECT_EQ(fs::file_size(bakery_yaml, ec), 2);
        EXPECT_EQ(fs::file_size(user_yaml, ec), 1);
    }

    // private file and local
    {
        SimulateWatoInstall(lwa_dir, pd_dir);
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto u_name = "check_mk";
        CreateIniFile(lwa_dir, not_bakeryfile, u_name);
        auto l_name = "check_mk_local";
        CreateIniFile(lwa_dir, not_bakeryfile_strange, l_name);

        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_TRUE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        // local changed
        EXPECT_EQ(fs::file_size(bakery_yaml, ec), 2);
        EXPECT_GE(fs::file_size(user_yaml, ec), 50);
    }

    // no private file and local
    {
        SimulateWatoInstall(lwa_dir, pd_dir);
        ON_OUT_OF_SCOPE(tst::SafeCleanTempDir("in");
                        tst::SafeCleanTempDir("out"););
        auto u_name = "check_mk";
        CreateIniFile(lwa_dir, not_bakeryfile, u_name);
        auto l_name = "check_mk_local";
        CreateIniFile(lwa_dir, not_bakeryfile_strange, l_name);

        auto local_exists = ConvertLocalIniFile(lwa_dir, pd_dir);
        ASSERT_TRUE(local_exists);
        auto user_exists = ConvertUserIniFile(lwa_dir, pd_dir, local_exists);
        // local changed
        EXPECT_EQ(fs::file_size(bakery_yaml, ec), 2);
        EXPECT_GE(fs::file_size(user_yaml, ec), 50);
    }
}

TEST(UpgradeTest, LoadIni) {
    cma::OnStartTest();

    auto temp_fs{tst::TempCfgFs::Create()};
    fs::path install_yml{fs::path(dirs::kFileInstallDir) /
                         files::kInstallYmlFileW};

    // #TODO (sk): make an API in TempCfgFs
    ASSERT_TRUE(temp_fs->createRootFile(
        install_yml, "# Packaged\nglobal:\n  enabled: yes\n  install: no"));

    fs::path temp_dir = cma::cfg::GetTempDir();

    auto normal_dir =
        temp_dir.wstring().find(L"\\tmp", 0) != std::wstring::npos;
    ASSERT_TRUE(normal_dir) << "tmp dir invalid " << temp_dir;

    std::error_code ec;
    auto lwa_dir = temp_dir / "in";
    auto pd_dir = temp_dir / "out";
    fs::create_directories(lwa_dir, ec);
    fs::create_directories(pd_dir, ec);

    {
        auto a1 = MakeComments("[a]", true);
        EXPECT_TRUE(a1.find("WATO", 0) != std::string::npos);
        EXPECT_TRUE(a1.find("[a]", 0) != std::string::npos);
        auto table = cma::tools::SplitString(a1, "\n");
        EXPECT_EQ(table.size(), 3);
        EXPECT_TRUE(table[0][0] == '#' && table[1][0] == '#');
        EXPECT_TRUE(table[2].size() == 0);
    }
    {
        auto a2 = MakeComments("[b]", false);
        EXPECT_TRUE(a2.find("WATO", 0) == std::string::npos);
        EXPECT_TRUE(a2.find("[b]", 0) != std::string::npos);
        auto table = cma::tools::SplitString(a2, "\n");
        EXPECT_EQ(table.size(), 3);
        EXPECT_TRUE(table[0][0] == '#' && table[1][0] == '#');
        EXPECT_TRUE(table[2].size() == 0);
    }

    {
        auto name = "nullfile";
        auto ini = CreateIniFile(lwa_dir, nullfile, name);
        auto yaml_file = CreateUserYamlFromIni(ini, pd_dir, name);
        EXPECT_FALSE(IsBakeryIni(ini));
        EXPECT_TRUE(yaml_file.empty());
        yaml_file = CreateBakeryYamlFromIni(ini, pd_dir, name);
        EXPECT_FALSE(IsBakeryIni(ini));
        EXPECT_TRUE(yaml_file.empty());
    }

    {
        auto name = "bakeryfile";
        auto ini = CreateIniFile(lwa_dir, bakeryfile, name);
        EXPECT_TRUE(IsBakeryIni(ini));
        auto yaml_file = CreateBakeryYamlFromIni(ini, pd_dir, name);
        EXPECT_EQ(yaml_file.filename().wstring(),
                  wtools::ConvertToUTF16(name) + files::kDefaultBakeryExt);
        auto yaml = YAML::LoadFile(yaml_file.u8string());
        EXPECT_TRUE(yaml.IsMap());
    }

    {
        // check that any file we could load as local
        auto name = "bakeryfile";
        auto ini = CreateIniFile(lwa_dir, bakeryfile, name);
        auto yaml_file = CreateUserYamlFromIni(ini, pd_dir, name);
        EXPECT_TRUE(IsBakeryIni(ini));
        EXPECT_EQ(yaml_file.filename().wstring(),
                  wtools::ConvertToUTF16(name) + files::kDefaultUserExt);
        auto yaml = YAML::LoadFile(yaml_file.u8string());
        EXPECT_TRUE(yaml.IsMap());
    }

    {
        auto name = "not_bakeryfile";
        auto ini = CreateIniFile(lwa_dir, not_bakeryfile, name);
        auto yaml_file = CreateBakeryYamlFromIni(ini, pd_dir, name);
        EXPECT_FALSE(IsBakeryIni(ini));
        auto yaml = YAML::LoadFile(yaml_file.u8string());
        EXPECT_EQ(yaml_file.filename().wstring(),
                  wtools::ConvertToUTF16(name) + files::kDefaultBakeryExt);
        EXPECT_TRUE(yaml.IsMap());
    }

    {
        auto name = "not_bakeryfile_strange";
        auto ini = CreateIniFile(lwa_dir, not_bakeryfile_strange, name);
        auto yaml_file = CreateUserYamlFromIni(ini, pd_dir, name);
        EXPECT_FALSE(IsBakeryIni(ini));
        auto yaml = YAML::LoadFile(yaml_file.u8string());
        EXPECT_EQ(yaml_file.filename().wstring(),
                  wtools::ConvertToUTF16(name) + files::kDefaultUserExt);
        EXPECT_TRUE(yaml.IsMap());
    }
}

TEST(UpgradeTest, CopyFoldersApi) {
    namespace fs = std::filesystem;

    EXPECT_TRUE(IsFileNonCompatible("Cmk-updatE-Agent.exe"));
    EXPECT_TRUE(IsFileNonCompatible("c:\\Cmk-updatE-Agent.exe"));
    EXPECT_FALSE(IsFileNonCompatible("cmk_update_agent.exe"));
    EXPECT_FALSE(IsFileNonCompatible("c:\\cmk_update_agent.exe"));

    EXPECT_TRUE(IsPathProgramData("checkmk/agent"));
    EXPECT_TRUE(IsPathProgramData("c:\\Checkmk/agent"));
    EXPECT_TRUE(IsPathProgramData("c:\\Checkmk\\Agent"));

    EXPECT_FALSE(IsPathProgramData("Checkmk_Agent"));
    EXPECT_FALSE(IsPathProgramData("Check\\mkAgent"));
    EXPECT_FALSE(IsPathProgramData("c:\\Check\\mkAgent"));

    fs::path base = cma::cfg::GetTempDir();
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););

    fs::path file_path = base / "marker.tmpx";
    {
        std::ofstream ofs(file_path);

        ASSERT_TRUE(ofs) << "Can't open file " << file_path.u8string()
                         << "error " << GetLastError() << "\n";
        ofs << "@marker\n";
    }

    std::error_code ec;
    {
        EXPECT_FALSE(fs::is_directory(file_path, ec));
        auto ret = CreateFolderSmart(file_path);
        EXPECT_TRUE(ret);
        EXPECT_TRUE(fs::is_directory(file_path, ec));
    }

    {
        auto test_path = base / "plugin";
        EXPECT_FALSE(fs::exists(test_path, ec));
        auto ret = CreateFolderSmart(test_path);
        EXPECT_TRUE(ret);
        EXPECT_TRUE(fs::is_directory(base / "plugin", ec));
    }

    {
        auto test_path = base / "mrpe";
        EXPECT_FALSE(fs::exists(test_path, ec));
        fs::create_directories(test_path);
        auto ret = CreateFolderSmart(test_path);
        EXPECT_TRUE(ret);
        EXPECT_TRUE(fs::is_directory(test_path, ec));
    }
}

static auto a1 =
    "AlignmentFixupsPersec|Caption|ContextSwitchesPersec|Description|ExceptionDispatchesPersec|FileControlBytesPersec|FileControlOperationsPersec|FileDataOperationsPersec|FileReadBytesPersec|FileReadOperationsPersec|FileWriteBytesPersec|FileWriteOperationsPersec|FloatingEmulationsPersec|Frequency_Object|Frequency_PerfTime|Frequency_Sys100NS|Name|PercentRegistryQuotaInUse|PercentRegistryQuotaInUse_Base|Processes|ProcessorQueueLength|SystemCallsPersec|SystemUpTime|Threads|Timestamp_Object|Timestamp_PerfTime|Timestamp_Sys100NS|WMIStatus";
static auto a2 =
    "8753143349248||8757138597559||8753154542256|1668537305287|952521535002|951235405633|25314498833504|950257251850|3054676197176|950165926199|949187772416|10000000|2435538|10000000||949554799728|951335256063|949187772535|949187772416|952503978051|132104050924847952|949187774233|132134863734478619|7504388659458|132134935734470000|OK";

TEST(UpgradeTest, CopyFolders) {
    namespace fs = std::filesystem;

    auto temp_fs{tst::TempCfgFs::Create()};
    auto [lwa_path, tgt] = tst::CreateInOut();
    fs::create_directory(lwa_path / "config");
    fs::create_directory(lwa_path / "plugins");
    fs::create_directory(lwa_path / "bin");
    tst::CreateWorkFile(lwa_path / "config" / "1.txt", "1");
    tst::CreateWorkFile(lwa_path / "plugins" / "2.txt", "2");
    auto good_path = fs::path{cma::cfg::GetTempDir()} /
                     cma::cfg::kAppDataCompanyName / kAppDataAppName;
    fs::create_directories(good_path);

    auto source_file = lwa_path / "marker.tmpx";
    {
        std::ofstream ofs(source_file);

        ASSERT_TRUE(ofs) << "Can't open file " << source_file.u8string()
                         << "error " << GetLastError() << "\n";
        ofs << "@marker\n";
    }
    auto count_root = CopyRootFolder(lwa_path, cma::cfg::GetTempDir());
    EXPECT_GE(count_root, 1);

    count_root = CopyRootFolder(lwa_path, cma::cfg::GetTempDir());
    EXPECT_GE(count_root, 0);

    fs::path target_file = cma::cfg::GetTempDir();
    target_file /= "marker.tmpx";
    std::error_code ec;
    EXPECT_TRUE(fs::exists(target_file, ec));

    auto count = CopyAllFolders(lwa_path, L"c:\\Users\\Public",
                                CopyFolderMode::keep_old);
    ASSERT_TRUE(count == 0)
        << "CopyAllFolders works only for ProgramData due to safety reasons";

    count = CopyAllFolders(lwa_path, cma::cfg::GetTempDir(),
                           CopyFolderMode::remove_old);

    EXPECT_EQ(count, 0);
    count = CopyAllFolders(lwa_path, good_path, CopyFolderMode::remove_old);
    EXPECT_EQ(count, 2);

    count = CopyAllFolders(lwa_path, good_path, CopyFolderMode::keep_old);
    EXPECT_EQ(count, 0);
}

TEST(UpgradeTest, CopyFiles) {
    namespace fs = std::filesystem;
    auto temp_fs{tst::TempCfgFs::Create()};
    auto [lwa_path, tgt] = tst::CreateInOut();
    fs::create_directory(lwa_path / "config");
    fs::create_directory(lwa_path / "plugins");
    fs::create_directory(lwa_path / "bin");
    tst::CreateWorkFile(lwa_path / "config" / "1.txt", "1");
    tst::CreateWorkFile(lwa_path / "plugins" / "2.txt", "2");
    tst::CreateWorkFile(lwa_path / "bin" / "3.txt", "3");
    tst::CreateWorkFile(lwa_path / "bin" / "4.txt", "4");
    auto good_path = fs::path{cma::cfg::GetTempDir()} /
                     cma::cfg::kAppDataCompanyName / kAppDataAppName;
    fs::create_directories(good_path);

    auto count = CopyFolderRecursive(
        lwa_path, cma::cfg::GetTempDir(), fs::copy_options::overwrite_existing,
        [lwa_path](fs::path P) {
            XLOG::l.i("Copy '{}' to '{}'", fs::relative(P, lwa_path),
                      wtools::ToUtf8(cma::cfg::GetTempDir()));
            return true;
        });
    EXPECT_EQ(count, 4);

    count = CopyFolderRecursive(
        lwa_path, cma::cfg::GetTempDir(), fs::copy_options::skip_existing,
        [lwa_path](fs::path path) {
            XLOG::l.i("Copy '{}' to '{}'", fs::relative(path, lwa_path),
                      wtools::ToUtf8(cma::cfg::GetTempDir()));
            return true;
        });
    EXPECT_TRUE(count == 0);

    tst::SafeCleanTempDir();
}

TEST(UpgradeTest, IgnoreApi) {
    EXPECT_TRUE(details::IsIgnoredFile("adda/dsds.ini"));
    EXPECT_TRUE(details::IsIgnoredFile("dsds.log"));
    EXPECT_TRUE(details::IsIgnoredFile("adda/dsds.eXe"));
    EXPECT_TRUE(details::IsIgnoredFile("adda/dsds.tmP"));
    EXPECT_TRUE(details::IsIgnoredFile("uninstall_pluginS.BAT"));
    EXPECT_TRUE(details::IsIgnoredFile("uninstall_xxx.BAT"));
    EXPECT_FALSE(details::IsIgnoredFile("adda/dsds.CAP"));

    EXPECT_TRUE(details::IsIgnoredFile("plugins.CAP"));

    EXPECT_FALSE(details::IsIgnoredFile("aas.PY"));
    EXPECT_FALSE(details::IsIgnoredFile("aasAA."));
}

TEST(UpgradeTest, TopLevelApi_Long) {
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio)
            .w("Program is not elevated, testing is not possible");
        return;
    }
    wtools::KillProcessFully(L"check_mk_agent.exe", 1);

    // normally this is not mandatory, but we may have few OHM running
    wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);
    StopWindowsService(L"winring0_1_2_0");

    EXPECT_TRUE(FindActivateStartLegacyAgent(AddAction::start_ohm));
    // sleep below is required to wait till check mk restarts ohm.
    // during restart registry entry may disappear
    tools::sleep(1000);
    EXPECT_TRUE(FindStopDeactivateLegacyAgent());
    EXPECT_TRUE(FindActivateStartLegacyAgent());
    // sleep below is required to wait till check mk restarts ohm.
    // during restart registry entry may disappear
    tools::sleep(2000);
    EXPECT_TRUE(FindStopDeactivateLegacyAgent());
}

TEST(UpgradeTest, StopStartStopOhmIntegration) {
    auto lwa_path = FindLegacyAgent();
    if (!lwa_path.empty()) {
        GTEST_SKIP()
            << "Legacy Agent is absent. Either install it or simulate it";
    }

    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio)
            .w("Program is not elevated, testing is not possible");
        return;
    }

    // start
    fs::path ohm = lwa_path;
    ohm /= "bin";
    ohm /= "OpenHardwareMonitorCLI.exe";
    std::error_code ec;
    if (!fs::exists(ohm)) {
        xlog::sendStringToStdio(
            "OHM is not installed with LWA, further testing of OHM is skipped\n",
            xlog::internal::Colors::yellow);
        return;
    }
    ASSERT_TRUE(fs::exists(ohm))
        << "OpenHardwareMonitor not installed, please, add it to the Legacy Agent folder";
    auto ret = RunDetachedProcess(ohm.wstring());
    ASSERT_TRUE(ret);

    auto status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                                SERVICE_RUNNING, 5000);
    EXPECT_EQ(status, SERVICE_RUNNING);

    wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);
    StopWindowsService(L"winring0_1_2_0");
    status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                           SERVICE_STOPPED, 5000);
    EXPECT_EQ(status, SERVICE_STOPPED);

    ret = RunDetachedProcess(ohm.wstring());
    ASSERT_TRUE(ret);
    tools::sleep(1000);
    status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                           SERVICE_RUNNING, 5000);
    EXPECT_EQ(status, SERVICE_RUNNING);
}

TEST(UpgradeTest, FindLwa_Long) {
    namespace fs = std::filesystem;
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio)
            .w("The Program is not elevated, testing is not possible");
        return;
    }

    auto lwa_path = FindLegacyAgent();
    if (!lwa_path.empty()) {
        GTEST_SKIP()
            << "Legacy Agent is absent. Either install it or simulate it";
    }

    EXPECT_TRUE(ActivateLegacyAgent());
    EXPECT_TRUE(IsLegacyAgentActive())
        << "Probably you have no legacy agent installed";

    fs::path ohm = lwa_path;
    ohm /= "bin";
    ohm /= "OpenHardwareMonitorCLI.exe";
    std::error_code ec;
    if (!fs::exists(ohm, ec)) {
        xlog::sendStringToStdio(
            "OHM is not installed with LWA, testing is limited\n",
            xlog::internal::Colors::yellow);
        StartWindowsService(L"check_mk_agent");
        // wait for service status
        for (int i = 0; i < 5; ++i) {
            auto status = GetServiceStatusByName(L"check_mk_agent");
            if (status == SERVICE_RUNNING) break;
            XLOG::l.i("RETRY wait for 'running' status, current is [{}]",
                      status);
            cma::tools::sleep(1000);
        }

        // stop service
        StopWindowsService(L"check_mk_agent");
        // wait few seconds
        auto status = GetServiceStatusByName(L"check_mk_agent");
        if (status != SERVICE_STOPPED) {
            xlog::sendStringToStdio("Service Killed with a hammer\n",
                                    xlog::internal::Colors::yellow);
            wtools::KillProcessFully(L"check_mk_agent.exe", 9);

            status = SERVICE_STOPPED;
        }

        EXPECT_EQ(status, SERVICE_STOPPED);
        EXPECT_TRUE(DeactivateLegacyAgent());
        EXPECT_FALSE(IsLegacyAgentActive());
        return;
    }
    ASSERT_TRUE(fs::exists(ohm, ec))
        << "OpenHardwareMonitor not installed, please, add it to the Legacy Agent folder";

    // start
    RunDetachedProcess(ohm.wstring());
    cma::tools::sleep(1000);
    auto status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                                SERVICE_RUNNING, 5000);
    EXPECT_EQ(status, SERVICE_RUNNING);
    StartWindowsService(L"check_mk_agent");
    // wait for service status
    for (int i = 0; i < 5; ++i) {
        status = GetServiceStatusByName(L"check_mk_agent");
        if (status == SERVICE_RUNNING) break;
        XLOG::l.i("RETRY wait for 'running' status, current is [{}]", status);
        cma::tools::sleep(1000);
    }

    EXPECT_EQ(status, SERVICE_RUNNING);
    status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                           SERVICE_RUNNING, 5000);
    EXPECT_EQ(status, SERVICE_RUNNING);
    // now we have to be in the usual state of LWA

    // stop OHM trash
    wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);
    StopWindowsService(L"winring0_1_2_0");
    status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                           SERVICE_STOPPED, 5000);
    EXPECT_TRUE(status == SERVICE_STOPPED || status == 1060);

    // stop service
    StopWindowsService(L"check_mk_agent");
    // wait few seconds
    status = GetServiceStatusByName(L"check_mk_agent");
    if (status != SERVICE_STOPPED) {
        xlog::sendStringToStdio("Service Killed with a hammer\n",
                                xlog::internal::Colors::yellow);
        wtools::KillProcessFully(L"check_mk_agent.exe", 9);

        // normally this is not mandatory, but we may have few OHM running
        wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);
        status = SERVICE_STOPPED;
    }

    EXPECT_EQ(status, SERVICE_STOPPED);
    EXPECT_TRUE(DeactivateLegacyAgent());
    EXPECT_FALSE(IsLegacyAgentActive());
}

}  // namespace cma::cfg::upgrade
