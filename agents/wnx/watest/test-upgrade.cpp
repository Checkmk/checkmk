// test-upgrade.cpp

// complicated things LWA -> NWA

#include "pch.h"

#include <filesystem>

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

static void CreateFile(std::filesystem::path Path, std::string Content) {
    std::ofstream ofs(Path);

    ofs << Content;
}

static auto CreateIniFile(std::filesystem::path Lwa, const std::string Content,
                          const std::string YamlName) {
    auto ini_file = Lwa / (YamlName + ".ini");
    CreateFile(Lwa / ini_file, Content);
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
    fs::path protocol_file = cma::cfg::GetTempDir();
    protocol_file /= cma::cfg::files::kUpgradeProtocol;
    auto x = CreateProtocolFile(protocol_file, "  aaa: aaa");
    ASSERT_TRUE(x);
    auto f = cma::tools::ReadFileInVector(protocol_file);
    ASSERT_TRUE(f.has_value());
    auto file_content = f.value();
    std::string str((const char*)file_content.data(), file_content.size());
    auto table = cma::tools::SplitString(str, "\n");
    EXPECT_EQ(table.size(), 3);
}

TEST(UpgradeTest, OnlyUserIni) {
    using namespace cma::cfg;
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    auto [lwa_dir, pd_dir] = CreateInOut();
    ASSERT_TRUE(!lwa_dir.empty() && !pd_dir.empty());

    std::error_code ec;

    auto expected_bakery_name =
        pd_dir / dirs::kBakery / files::kDefaultMainConfigName;
    expected_bakery_name += files::kDefaultBakeryExt;
    auto expected_user_name = pd_dir / files::kDefaultMainConfigName;
    expected_user_name += files::kDefaultUserExt;

    // usual file
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

    // bakery file
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

    // non_bakery file + local
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
    }

    // bakery file + local
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

TEST(UpgradeTest, LoadIni) {
    tst::SafeCleanTempDir();
    namespace fs = std::filesystem;
    fs::path temp_dir = cma::cfg::GetTempDir();
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
        EXPECT_TRUE(a1.find("bakery", 0) != std::string::npos);
        EXPECT_TRUE(a1.find("[a]", 0) != std::string::npos);
        auto table = cma::tools::SplitString(a1, "\n");
        EXPECT_EQ(table.size(), 3);
        EXPECT_TRUE(table[0][0] == '#' && table[1][0] == '#');
        EXPECT_TRUE(table[2].size() == 0);
    }
    {
        auto a2 = MakeComments("[b]", false);
        EXPECT_TRUE(a2.find("bakery", 0) == std::string::npos);
        EXPECT_TRUE(a2.find("[b]", 0) != std::string::npos);
        auto table = cma::tools::SplitString(a2, "\n");
        EXPECT_EQ(table.size(), 3);
        EXPECT_TRUE(table[0][0] == '#' && table[1][0] == '#');
        EXPECT_TRUE(table[2].size() == 0);
    }

    {
        auto name = "nullfile";
        auto ini = CreateIniFile(lwa_dir, nullfile, name);
        auto yaml_file = CreateYamlFromIniSmart(ini, pd_dir, name);
        EXPECT_FALSE(IsBakeryIni(ini));
        EXPECT_TRUE(yaml_file.empty());
    }

    {
        auto name = "bakeryfile";
        auto ini = CreateIniFile(lwa_dir, bakeryfile, name);
        auto yaml_file = CreateYamlFromIniSmart(ini, pd_dir, name);
        EXPECT_TRUE(IsBakeryIni(ini));
        auto yaml = YAML::LoadFile(yaml_file.u8string());
        EXPECT_TRUE(yaml.IsMap());
    }
    {
        auto name = "not_bakeryfile";
        auto ini = CreateIniFile(lwa_dir, not_bakeryfile, name);
        auto yaml_file = CreateYamlFromIniSmart(ini, pd_dir, name);
        EXPECT_FALSE(IsBakeryIni(ini));
        auto yaml = YAML::LoadFile(yaml_file.u8string());
        EXPECT_TRUE(yaml.IsMap());
    }
    {
        auto name = "not_bakeryfile_strange";
        auto ini = CreateIniFile(lwa_dir, not_bakeryfile_strange, name);
        auto yaml_file = CreateYamlFromIniSmart(ini, pd_dir, name);
        EXPECT_FALSE(IsBakeryIni(ini));
        auto yaml = YAML::LoadFile(yaml_file.u8string());
        EXPECT_TRUE(yaml.IsMap());
    }

    tst::SafeCleanTempDir();
}  // namespace cma::cfg::upgrade

TEST(UpgradeTest, CopyFolders) {
    namespace fs = std::filesystem;
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio)
            .w("The Program is not elevated, testing is not possible");
        return;
    }
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

    fs::path target_file = cma::cfg::GetTempDir();
    target_file /= "marker.tmpx";
    std::error_code ec;
    EXPECT_TRUE(fs::exists(target_file, ec));

    auto count = CopyAllFolders(path, cma::cfg::GetTempDir());
    EXPECT_GE(count, 5);

    ON_OUT_OF_SCOPE(fs::remove(target_file, ec));
    ON_OUT_OF_SCOPE(fs::remove(source_file, ec));

    tst::SafeCleanTempDir();
}

TEST(UpgradeTest, CopyFiles) {
    namespace fs = std::filesystem;
    fs::path path = FindLegacyAgent();
    ASSERT_TRUE(!path.empty())
        << "Legacy Agent is absent. Either install it or simulate it";

    auto count =
        CopyFolderRecursive(path, cma::cfg::GetTempDir(), [path](fs::path P) {
            XLOG::l.i("Copy '{}' to '{}'", fs::relative(P, path).u8string(),
                      wtools::ConvertToUTF8(cma::cfg::GetTempDir()));
            return true;
        });
    EXPECT_TRUE(count > 4);

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

TEST(UpgradeTest, TopLevelApi) {
    if (!cma::tools::win::IsElevated()) {
        XLOG::l(XLOG::kStdio)
            .w("Program is not elevated, testing is not possible");
        return;
    }
    wtools::KillProcess(L"check_mk_agent.exe", 1);
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

TEST(UpgradeTest, FindLwa) {
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
    ASSERT_TRUE(fs::exists(ohm, ec))
        << "OpenHardwareMonitor not installed, please, add it to the Legacy Agent folder";

    // start
    RunDetachedProcess(ohm.wstring());
    auto status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                                SERVICE_RUNNING, 5000);
    EXPECT_EQ(status, SERVICE_RUNNING);
    StartWindowsService(L"check_mk_agent");
    status = GetServiceStatusByName(L"check_mk_agent");
    EXPECT_EQ(status, SERVICE_RUNNING);
    status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                           SERVICE_RUNNING, 5000);
    EXPECT_EQ(status, SERVICE_RUNNING);
    // now we have to be in the usual state of LWA

    // stop service
    StopWindowsService(L"check_mk_agent");
    status = GetServiceStatusByName(L"check_mk_agent");
    EXPECT_EQ(status, SERVICE_STOPPED);
    EXPECT_TRUE(DeactivateLegacyAgent());
    EXPECT_FALSE(IsLegacyAgentActive());
    wtools::KillProcess(L"Openhardwaremonitorcli.exe", 1);
    StopWindowsService(L"winring0_1_2_0");
    status = WaitForStatus(GetServiceStatusByName, L"WinRing0_1_2_0",
                           SERVICE_STOPPED, 5000);
    EXPECT_EQ(status, SERVICE_STOPPED);
}

}  // namespace cma::cfg::upgrade
