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

namespace cma::cfg::upgrade {

std::string nullfile = "";
std::string commentfile =
    "# This file is managed via WATO, do not edit manually or you \n";
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
        temp_dir.wstring().find(L"\\temp", 0) != std::wstring::npos;
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
    std::string str((const char*)file_content.data(), file_content.size());
    auto table = cma::tools::SplitString(str, "\n");
    EXPECT_EQ(table.size(), 3);
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

TEST(UpgradeTest, UserIniPackagedAgent) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
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

void SimulateWatoInstall(std::filesystem::path pd_dir) {
    namespace fs = std::filesystem;
    auto bakery_yaml = ConstructBakeryYmlPath(pd_dir);
    auto user_yaml = ConstructUserYmlPath(pd_dir);
    std::error_code ec;
    fs::create_directory(pd_dir / dirs::kBakery, ec);
    ASSERT_EQ(ec.value(), 0);
    tst::ConstructFile(bakery_yaml, "11");
    tst::ConstructFile(user_yaml, "0");
}

TEST(UpgradeTest, UserIniWatoAgent) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    auto [lwa_dir, pd_dir] = CreateInOut();
    ASSERT_TRUE(!lwa_dir.empty() && !pd_dir.empty());

    cma::cfg::SetTestInstallationType(InstallationType::wato);
    ON_OUT_OF_SCOPE(
        cma::cfg::SetTestInstallationType(InstallationType::packaged));

    std::error_code ec;

    // SIMULATE wato agent installation
    auto bakery_yaml = ConstructBakeryYmlPath(pd_dir);
    auto user_yaml = ConstructUserYmlPath(pd_dir);

    // bakery file and no local
    {
        SimulateWatoInstall(pd_dir);
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
        SimulateWatoInstall(pd_dir);
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
        SimulateWatoInstall(pd_dir);
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
        SimulateWatoInstall(pd_dir);
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
        SimulateWatoInstall(pd_dir);
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
    tst::SafeCleanTempDir();
    namespace fs = std::filesystem;
    fs::path temp_dir = cma::cfg::GetTempDir();
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););

    auto normal_dir =
        temp_dir.wstring().find(L"\\temp", 0) != std::wstring::npos;
    ASSERT_TRUE(normal_dir) << "temp dir invalid " << temp_dir;

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

    EXPECT_TRUE(IsPathProgramData("Checkmk/Agent"));
    EXPECT_TRUE(IsPathProgramData("c:\\Checkmk/Agent"));
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

TEST(UpgradeTest, CopyFolders) {
    namespace fs = std::filesystem;
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio)
            .w("The Program is not elevated, testing is not possible");
        return;
    }
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););

    fs::path path = FindLegacyAgent();
    ASSERT_TRUE(!path.empty())
        << "Legacy Agent is absent. Either install it or simulate it";

    auto source_file = path / "marker.tmpx";
    {
        std::ofstream ofs(source_file);

        ASSERT_TRUE(ofs) << "Can't open file " << source_file.u8string()
                         << "error " << GetLastError() << "\n";
        ofs << "@marker\n";
    }
    auto count_root = CopyRootFolder(path, cma::cfg::GetTempDir());
    EXPECT_GE(count_root, 1);

    count_root = CopyRootFolder(path, cma::cfg::GetTempDir());
    EXPECT_GE(count_root, 0);

    fs::path target_file = cma::cfg::GetTempDir();
    target_file /= "marker.tmpx";
    std::error_code ec;
    EXPECT_TRUE(fs::exists(target_file, ec));

    auto count =
        CopyAllFolders(path, L"c:\\Users\\Public", CopyFolderMode::keep_old);
    ASSERT_TRUE(count == 0)
        << "CopyAllFolders works only for ProgramData due to safety reasons";

    count = CopyAllFolders(path, cma::cfg::GetTempDir(),
                           CopyFolderMode::remove_old);
    EXPECT_GE(count, 5);

    count =
        CopyAllFolders(path, cma::cfg::GetTempDir(), CopyFolderMode::keep_old);
    EXPECT_EQ(count, 0);

    ON_OUT_OF_SCOPE(fs::remove(target_file, ec));
    ON_OUT_OF_SCOPE(fs::remove(source_file, ec));
}

TEST(UpgradeTest, CopyFiles) {
    namespace fs = std::filesystem;
    fs::path path = FindLegacyAgent();
    ASSERT_TRUE(!path.empty())
        << "Legacy Agent is absent. Either install it or simulate it";

    auto count = CopyFolderRecursive(
        path, cma::cfg::GetTempDir(), fs::copy_options::overwrite_existing,
        [path](fs::path P) {
            XLOG::l.i("Copy '{}' to '{}'", fs::relative(P, path).u8string(),
                      wtools::ConvertToUTF8(cma::cfg::GetTempDir()));
            return true;
        });
    EXPECT_TRUE(count > 4);

    count = CopyFolderRecursive(
        path, cma::cfg::GetTempDir(), fs::copy_options::skip_existing,
        [path](fs::path P) {
            XLOG::l.i("Copy '{}' to '{}'", fs::relative(P, path).u8string(),
                      wtools::ConvertToUTF8(cma::cfg::GetTempDir()));
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

TEST(UpgradeTest, StopStartStopOhm) {
    namespace fs = std::filesystem;
    auto path = FindLegacyAgent();
    ASSERT_TRUE(!path.empty())
        << "Legacy Agent is absent. Either install it or simulate it";

    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio)
            .w("Program is not elevated, testing is not possible");
        return;
    }

    // start
    fs::path ohm = path;
    ohm /= "bin";
    ohm /= "OpenHardwareMonitorCLI.exe";
    std::error_code ec;
    if (!fs::exists(ohm)) {
        xlog::sendStringToStdio(
            "OHM is not installed with LWA, further testing of OHM is skipped\n",
            xlog::internal::Colors::kYellow);
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

    auto path = FindLegacyAgent();
    ASSERT_TRUE(!path.empty())
        << "Legacy Agent is absent. Either install it or simulate it";

    EXPECT_TRUE(ActivateLegacyAgent());
    EXPECT_TRUE(IsLegacyAgentActive())
        << "Probably you have no legacy agent installed";

    fs::path ohm = path;
    ohm /= "bin";
    ohm /= "OpenHardwareMonitorCLI.exe";
    std::error_code ec;
    if (!fs::exists(ohm, ec)) {
        xlog::sendStringToStdio(
            "OHM is not installed with LWA, testing is limited\n",
            xlog::internal::Colors::kYellow);
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
                                    xlog::internal::Colors::kYellow);
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
                                xlog::internal::Colors::kYellow);
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
