// test-cap.cpp:
// Installation of cap files

#include "pch.h"

#include <filesystem>

#include "cap.h"
#include "cfg.h"
#include "lwa/types.h"
#include "read_file.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"
#include "yaml-cpp/yaml.h"

namespace cma::cfg::cap {

TEST(CapTest, CheckIsFilesTheSame) {
    EXPECT_TRUE(IsFilesTheSame("c:\\windows\\explorer.exe",
                               "c:\\windows\\explorer.exe"));
    EXPECT_FALSE(IsFilesTheSame("c:\\windows\\explorer.exe",
                                "c:\\windows\\HelpPane.exe"));

    EXPECT_FALSE(
        IsFilesTheSame("c:\\windows\\explorer.exe", "c:\\windows\\ssd.exe"));
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    auto [file1, file2] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););
    // source without target
    std::string name = "a.txt";
    {
        tst::ConstructFile(file1 / name, "abcde0");
        tst::ConstructFile(file2 / name, "abcde1");
        EXPECT_FALSE(IsFilesTheSame(file1 / name, file2 / name));
        EXPECT_TRUE(NeedReinstall(file2 / name, file1 / name));
    }
}

TEST(CapTest, Reinstall) {
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    auto [source, target] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););
    std::error_code ec;

    EXPECT_NO_THROW(NeedReinstall("", ""));
    EXPECT_NO_THROW(NeedReinstall("wdwd::::", "\\acfefefvefvwefwegf"));
    std::string name = "a.txt";
    // absent source and target
    {
        EXPECT_FALSE(NeedReinstall(target / name, source / name));  //
    }

    // absent source
    {
        tst::ConstructFile(target / name, "a");
        EXPECT_FALSE(NeedReinstall(target / name, source / name));
    }

    tst::SafeCleanTempDir();
    tst::CreateInOut();
    // source without target
    {
        tst::ConstructFile(source / name, "a");
        EXPECT_TRUE(NeedReinstall(target / name, source / name));
    }

    // target is newer than source
    {
        tst::ConstructFile(target / name, "a");
        EXPECT_FALSE(NeedReinstall(target / name, source / name));
    }

    // source is newer than target
    {
        cma::tools::sleep(100);
        tst::ConstructFile(source / name, "a");
        EXPECT_TRUE(NeedReinstall(target / name, source / name));
    }

    // source is older than target, but content is not the same
    {
        cma::tools::sleep(100);
        tst::ConstructFile(source / name, "b");
        EXPECT_TRUE(NeedReinstall(source / name, target / name));
    }

    tst::SafeCleanTempDir();
}

TEST(CapTest, InstallFileAsCopy) {
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    auto [source, target] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););
    std::error_code ec;

    std::wstring file_name = L"check_mk.copy.tmp";
    auto target_file = target / file_name;
    auto source_file = source / file_name;

    fs::remove(target_file, ec);

    // absent source and target
    {
        bool res = true;
        EXPECT_NO_THROW(res =
                            InstallFileAsCopy(L"", L"", L"", Mode::normal));  //
        EXPECT_FALSE(res);

        EXPECT_NO_THROW(res = InstallFileAsCopy(L"sdf", L"c:\\", L"c:\\",
                                                Mode::normal));  //
        EXPECT_TRUE(res);

        EXPECT_NO_THROW(res = InstallFileAsCopy(L":\\\\wefewfw", L"sssssssss",
                                                L"scc", Mode::normal));  //
        EXPECT_FALSE(res);
    }

    // absent source
    {
        tst::ConstructFile(target_file, "1");
        EXPECT_TRUE(InstallFileAsCopy(file_name, target.wstring(),
                                      source.wstring(), Mode::normal));  //
        ASSERT_FALSE(fs::exists(target_file, ec)) << "must be removed";
    }

    // target presented
    {
        tst::ConstructFile(source_file, "2");
        EXPECT_TRUE(InstallFileAsCopy(file_name, target.wstring(),
                                      source.wstring(), Mode::normal));  //
        EXPECT_TRUE(fs::exists(target_file, ec)) << "must be presented";
    }
}

TEST(CapTest, PackagedAgent) {
    namespace fs = std::filesystem;

    // check we have code compatible with installation
    auto ini_path = fs::current_path();
    ini_path /= "check_mk.ini";
    std::error_code ec;
    if (fs::exists(ini_path, ec)) {
        EXPECT_TRUE(IsIniFileFromInstaller(ini_path));
    } else
        XLOG::SendStringToStdio(
            fmt::format(
                "Skipping Cap packagedAgen internal TEST, no file '{}'\n",
                ini_path.string()),
            XLOG::Colors::yellow);

    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););

    EXPECT_FALSE(IsIniFileFromInstaller(""));
    fs::path base = cma::cfg::GetTempDir();
    fs::path from_bakery = base / "from_bakery.ini";
    {
        std::ofstream ofs(from_bakery);

        ASSERT_TRUE(ofs) << "Can't open file " << from_bakery.u8string()
                         << "error " << GetLastError() << "\n";
        ofs << "# Created by Check_MK Agent Bakery.\n"
               "# This file is managed via WATO, do not edit manually or you\n"
               "# lose your changes next time when you update the agent.\n"
               "[global] \n";
    }

    EXPECT_FALSE(IsIniFileFromInstaller(from_bakery));

    fs::path valid_file = base / "valid_file.ini";
    {
        std::ofstream ofs(valid_file);

        ASSERT_TRUE(ofs) << "Can't open file " << valid_file.u8string()
                         << "error " << GetLastError() << "\n";
        ofs << kIniFromInstallMarker << "\n";
    }

    EXPECT_TRUE(IsIniFileFromInstaller(valid_file));
}

TEST(CapTest, InstallIni) {
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    tst::SafeCleanBakeryDir();
    auto [source, target] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(); tst::SafeCleanBakeryDir(););
    std::error_code ec;

    std::string ini_name = "check_mk.ini";
    fs::path ini_base = cma::cfg::GetUserDir();
    ini_base /= "check_mk.test.ini";
    ASSERT_TRUE(fs::exists(ini_base, ec));
    auto ini_target = target / ini_name;
    auto ini_source = source / ini_name;

    auto bakery_yml = cma::cfg::GetBakeryFile();
    fs::remove(bakery_yml, ec);

    // absent source and target
    {
        EXPECT_NO_THROW(ReinstallIni("", ""));                       //
        EXPECT_NO_THROW(ReinstallIni(":\\\\wefewfw", "sssssssss"));  //
        EXPECT_TRUE(ReinstallIni(ini_target, ini_source));           //
    }

    // absent source
    {
        tst::ConstructFile(bakery_yml, "1");
        tst::ConstructFile(ini_target, "1");
        EXPECT_TRUE(ReinstallIni(ini_target, ini_source));  //
        EXPECT_FALSE(fs::exists(bakery_yml, ec)) << "must be removed";
        EXPECT_FALSE(fs::exists(ini_target, ec)) << "must be removed";
    }

    // target presented
    {
        fs::copy_file(ini_base, ini_source, ec);
        EXPECT_TRUE(ReinstallIni(ini_target, ini_source));  //
        EXPECT_TRUE(fs::exists(bakery_yml, ec)) << "must be presented";
        EXPECT_TRUE(fs::exists(ini_target, ec)) << "must be presented";
    }
}

TEST(CapTest, InstallCap) {
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    auto [source, target] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););
    std::error_code ec;

    std::string cap_name = "plugins.cap";
    fs::path cap_base = cma::cfg::GetUserDir();
    cap_base /= "plugins.test.cap";
    fs::path cap_null = cma::cfg::GetUserDir();
    cap_null /= "plugins_null.test.cap";
    ASSERT_TRUE(fs::exists(cap_base, ec));
    auto cap_in = target / cap_name;
    auto cap_out = source / cap_name;
    fs::path plugin1 = cma::cfg::GetUserPluginsDir();
    fs::path plugin2 = cma::cfg::GetUserPluginsDir();
    plugin1 /= "mk_inventory.vbs";
    plugin2 /= "windows_if.ps1";

    // absent source and target
    {
        EXPECT_FALSE(ReinstallCaps(cap_out, cap_in));  //
    }

    // absent source
    {
        tst::ConstructFile(plugin1, "1");
        tst::ConstructFile(plugin2, "2");
        fs::copy_file(cap_base, cap_out, ec);
        EXPECT_TRUE(ReinstallCaps(cap_out, cap_in));  //
        EXPECT_FALSE(fs::exists(cap_out, ec)) << "file must be deleted";
        EXPECT_FALSE(fs::exists(plugin1, ec)) << "file must be removed";
        EXPECT_FALSE(fs::exists(plugin2, ec)) << "file must be removed";
    }

    // absent target
    {
        fs::remove(cap_out, ec);
        fs::remove(plugin1, ec);
        fs::remove(plugin2, ec);
        fs::copy_file(cap_base, cap_in, ec);
        ASSERT_EQ(ec.value(), 0);
        EXPECT_TRUE(ReinstallCaps(cap_out, cap_in));  //
        EXPECT_TRUE(fs::exists(cap_out, ec)) << "file must exists";
        EXPECT_TRUE(fs::exists(plugin1, ec)) << "file must exists";
        EXPECT_TRUE(fs::exists(plugin2, ec)) << "file must exists";
    }

    // source is null
    {
        fs::remove(cap_in, ec);
        fs::copy_file(cap_null, cap_in, ec);
        ASSERT_EQ(ec.value(), 0);
        EXPECT_TRUE(ReinstallCaps(cap_out, cap_in));  //
        EXPECT_TRUE(fs::exists(cap_out, ec)) << "file must exists";
        EXPECT_FALSE(fs::exists(plugin1, ec)) << "file must be removed";
        EXPECT_FALSE(fs::exists(plugin2, ec)) << "file must be removed";
    }
}

TEST(CapTest, Check) {
    namespace fs = std::filesystem;
    std::string name = "a/b.txt";
    auto out = ProcessPluginPath(name);
    fs::path expected_path = cma::cfg::GetUserDir() + L"\\a\\b.txt";
    EXPECT_EQ(out, expected_path.lexically_normal());
}

TEST(CapTest, IsAllowedToKill) {
    using namespace cma::cfg;
    cma::OnStartTest();
    ON_OUT_OF_SCOPE(cma::OnStartTest());

    EXPECT_FALSE(IsAllowedToKill(L"smss_log.exe"));
    EXPECT_TRUE(IsAllowedToKill(L"cMk-upDate-agent.exe"));
    EXPECT_TRUE(IsAllowedToKill(L"MK_LOGWATCH.exe"));
    EXPECT_TRUE(IsAllowedToKill(L"MK_JOLOKIA.exe"));

    auto yaml = cma::cfg::GetLoadedConfig();
    yaml[groups::kGlobal][vars::kTryKillPluginProcess] =
        YAML::Load(values::kTryKillNo);
    EXPECT_FALSE(IsAllowedToKill(L"cMk-upDate-agent.exe"));
    EXPECT_FALSE(IsAllowedToKill(L"MK_LOGWATCH.exe"));
    EXPECT_FALSE(IsAllowedToKill(L"MK_JOLOKIA.exe"));

    yaml[groups::kGlobal][vars::kTryKillPluginProcess] = YAML::Load("aaa");
    EXPECT_FALSE(IsAllowedToKill(L"cMk-upDate-agent.exe"));
    EXPECT_FALSE(IsAllowedToKill(L"MK_LOGWATCH.exe"));
    EXPECT_FALSE(IsAllowedToKill(L"MK_JOLOKIA.exe"));

    yaml[groups::kGlobal][vars::kTryKillPluginProcess] =
        YAML::Load(values::kTryKillAll);
    EXPECT_TRUE(IsAllowedToKill(L"smss_log.exe"));
    EXPECT_TRUE(IsAllowedToKill(L"cMk-upDate-agent.exe"));
    EXPECT_TRUE(IsAllowedToKill(L"MK_LOGWATCH.exe"));
    EXPECT_TRUE(IsAllowedToKill(L"MK_JOLOKIA.exe"));
}

TEST(CapTest, GetProcessToKill) {
    cma::OnStartTest();
    EXPECT_TRUE(GetProcessToKill(L"").empty());
    EXPECT_TRUE(GetProcessToKill(L"smss.exe").empty());
    EXPECT_TRUE(GetProcessToKill(L"aaaaasmss.com").empty());
    EXPECT_TRUE(GetProcessToKill(L"aaaaasmss").empty());
    EXPECT_TRUE(GetProcessToKill(L"aaaaasmss").empty());
    EXPECT_TRUE(GetProcessToKill(L"c:\\windows\\system32\\ping.exe").empty());
    EXPECT_TRUE(GetProcessToKill(L"c:\\windows\\system32\\a_the_ping.eXe") ==
                L"a_the_ping.eXe");
}

TEST(CapTest, StoreFileAgressive) {
    ASSERT_TRUE(IsStoreFileAgressive()) << "should be set normally";

    using namespace std::chrono;
    namespace fs = std::filesystem;
    if (!cma::ConfigLoaded()) cma::OnStartTest();

    tst::SafeCleanTempDir();
    auto [work, _] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););

    fs::path ping(R"(c:\windows\system32\ping.exe)");
    if (!fs::exists(ping))
        GTEST_SKIP() << "there is no notepad to test something";
    fs::path cmk_test_ping = work / "cmk-update-aGent.exe";
    wtools::KillProcessFully(cmk_test_ping.filename().wstring());
    cma::tools::sleep(200ms);
    ASSERT_TRUE(fs::copy_file(ping, cmk_test_ping,
                              fs::copy_options::overwrite_existing));
    ASSERT_TRUE(cma::tools::RunDetachedCommand(cmk_test_ping.u8string() +
                                               " -t 8.8.8.8"));
    cma::tools::sleep(200ms);
    std::vector<char> buf = {'_', '_'};
    ASSERT_FALSE(StoreFile(cmk_test_ping, buf));
    ASSERT_TRUE(StoreFileAgressive(cmk_test_ping, buf, 1));
    ASSERT_TRUE(fs::copy_file(ping, cmk_test_ping,
                              fs::copy_options::overwrite_existing));
    ASSERT_TRUE(cma::tools::RunDetachedCommand(cmk_test_ping.u8string() +
                                               " -t 8.8.8.8"));
    cma::tools::sleep(200ms);

    std::error_code ec;
    fs::remove(cmk_test_ping, ec);
    ASSERT_FALSE(StoreFile(cmk_test_ping, buf));
    ASSERT_TRUE(StoreFileAgressive(cmk_test_ping, buf, 1));
}

TEST(CapTest, CheckValid) {
    namespace fs = std::filesystem;
    fs::path cap = cma::cfg::GetUserDir();
    cap /= "plugins.test.cap";
    std::error_code ec;
    ASSERT_TRUE(fs::exists(cap, ec)) << "Your setup for tests is invalid";
    std::vector<std::wstring> files;
    auto ret = Process(cap.u8string(), ProcMode::list, files);
    EXPECT_TRUE(ret);
    ASSERT_EQ(files.size(), 2);
    EXPECT_EQ(files[0], GetUserPluginsDir() + L"\\windows_if.ps1");
    EXPECT_EQ(files[1], GetUserPluginsDir() + L"\\mk_inventory.vbs");
}

TEST(CapTest, CheckNull) {
    namespace fs = std::filesystem;
    fs::path cap = cma::cfg::GetUserDir();
    cap /= "plugins_null.test.cap";
    std::error_code ec;
    ASSERT_TRUE(fs::exists(cap, ec)) << "Your setup for tests is invalid";
    std::vector<std::wstring> files;
    auto ret = Process(cap.u8string(), ProcMode::list, files);
    EXPECT_TRUE(ret);
    EXPECT_EQ(files.size(), 0);
}

TEST(CapTest, CheckUnpack) {
    namespace fs = std::filesystem;
    std::error_code ec;
    std::wstring names[] = {GetUserPluginsDir() + L"\\windows_if.ps1",
                            GetUserPluginsDir() + L"\\mk_inventory.vbs"};

    fs::path p = GetUserPluginsDir();
    // clean folder
    {
        auto normal_dir =
            p.u8string().find("\\plugins", 5) != std::wstring::npos;
        ASSERT_TRUE(normal_dir);
        if (normal_dir) {
            // clean
            fs::remove_all(p);
            fs::create_directory(p);
        } else
            return;
    }
    //
    auto f_string = p.lexically_normal().wstring();
    ASSERT_TRUE(f_string.find(L"ProgramData\\checkmk\\agent\\plugins"));
    for (auto& name : names) fs::remove(name, ec);

    fs::path cap = cma::cfg::GetUserDir();
    cap /= "plugins.test.cap";
    ASSERT_TRUE(fs::exists(cap, ec)) << "Your setup for tests is invalid";
    std::vector<std::wstring> files;
    auto ret = Process(cap.u8string(), ProcMode::install, files);
    EXPECT_TRUE(ret);
    ASSERT_EQ(files.size(), 2);
    EXPECT_EQ(files[0], names[0]);
    EXPECT_EQ(files[1], names[1]);

    for (auto& name : names) {
        EXPECT_TRUE(fs::exists(name, ec));
        fs::remove(name, ec);  // cleanup
    }
}

TEST(CapTest, CheckRemove) {
    namespace fs = std::filesystem;
    std::error_code ec;
    fs::path cap = cma::cfg::GetUserDir();
    cap /= "plugins.test.cap";

    // unpack cap into folder
    {
        ASSERT_TRUE(fs::exists(cap, ec)) << "Your setup for tests is invalid";
        std::vector<std::wstring> files;
        auto ret = Process(cap.u8string(), ProcMode::install, files);
        ASSERT_TRUE(ret);
    }

    std::wstring names[] = {GetUserPluginsDir() + L"\\windows_if.ps1",
                            GetUserPluginsDir() + L"\\mk_inventory.vbs"};
    namespace fs = std::filesystem;
    fs::path p = GetUserPluginsDir();
    auto f_string = p.lexically_normal().wstring();
    ASSERT_TRUE(f_string.find(L"ProgramData\\checkmk\\agent\\plugins"));
    for (auto& name : names) {
        EXPECT_TRUE(fs::exists(name, ec));
    }

    ASSERT_TRUE(fs::exists(cap, ec)) << "Your setup for tests is invalid";
    std::vector<std::wstring> files;
    auto ret = Process(cap.u8string(), ProcMode::remove, files);
    EXPECT_TRUE(ret);
    ASSERT_EQ(files.size(), 2);
    EXPECT_EQ(files[0], names[0]);
    EXPECT_EQ(files[1], names[1]);

    for (auto& name : names) {
        EXPECT_FALSE(fs::exists(name, ec));
    }
}

TEST(CapTest, CheckInValid) {
    namespace fs = std::filesystem;

    int i = 0;
    {
        fs::path invalid_cap = cma::cfg::GetUserDir();
        invalid_cap /= "plugins_invalid.test.cap";
        std::error_code ec;
        ASSERT_TRUE(fs::exists(invalid_cap, ec))
            << "Your setup for tests is invalid";
        std::vector<std::wstring> files;
        XLOG::l.i("Next log output should be crit. This is SUCCESS");
        auto ret = Process(invalid_cap.u8string(), ProcMode::list, files);
        EXPECT_FALSE(ret);
        ASSERT_EQ(files.size(), 1)
            << "this file is invalid, but first file should be ok";
    }

    {
        fs::path invalid_cap = cma::cfg::GetUserDir();
        invalid_cap /= "plugins_long.test.cap";
        std::error_code ec;
        ASSERT_TRUE(fs::exists(invalid_cap, ec))
            << "Your setup for tests is invalid";
        std::vector<std::wstring> files;
        auto ret = Process(invalid_cap.u8string(), ProcMode::list, files);
        EXPECT_FALSE(ret);
        ASSERT_EQ(files.size(), 2)
            << "this file is invalid, but first TWO files should be ok";
    }

    {
        fs::path invalid_cap = cma::cfg::GetUserDir();
        invalid_cap /= "plugins_short.test.cap";
        std::error_code ec;
        ASSERT_TRUE(fs::exists(invalid_cap, ec))
            << "Your setup for tests is invalid";
        std::vector<std::wstring> files;
        auto ret = Process(invalid_cap.u8string(), ProcMode::list, files);
        EXPECT_FALSE(ret);
        ASSERT_EQ(files.size(), 1)
            << "this file is invalid, but first file should be ok";
    }
}

TEST(CapTest, Names) {
    cma::OnStartTest();
    auto [t, s] = GetExampleYmlNames();
    std::filesystem::path t_expected = GetUserDir();
    t_expected /= files::kUserYmlFile;
    t_expected.replace_extension("example.yml");
    EXPECT_EQ(t.u8string(), t_expected.u8string());
    std::filesystem::path s_expected = GetRootInstallDir();
    EXPECT_EQ(s.u8string(), (s_expected / files::kUserYmlFile).u8string());
}

TEST(CapTest, ReInstallRestore) {
    using namespace cma::tools;
    cma::OnStartTest();
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    auto [r, u] = tst::CreateInOut();
    auto root = r.wstring();
    auto user = u.wstring();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););

    auto old_user = cma::cfg::GetUserDir();

    fs::path ini_base = old_user;
    ini_base /= "check_mk.ps.test.ini";
    fs::path cap_base = old_user;
    cap_base /= "plugins.test.cap";
    fs::path cap_null = old_user;
    cap_null /= "plugins_null.test.cap";

    std::error_code ec;
    try {
        fs::create_directory(r / dirs::kInstall);
        fs::copy_file(ini_base, r / dirs::kInstall / "check_mk.ini");
        fs::copy_file(cap_base, r / dirs::kInstall / "plugins.cap");
        tst::CreateWorkFile(r / dirs::kInstall / "checkmk.dat", "this");
    } catch (const std::exception& e) {
        ASSERT_TRUE(false) << "can't create file data exception is "
                           << e.what();
    }

    GetCfg().pushFolders(r, u);
    ON_OUT_OF_SCOPE(GetCfg().popFolders(););

    auto user_gen = [u](const std::wstring_view name) -> auto {
        return (u / dirs::kInstall / name).wstring();
    };

    auto root_gen = [r](const std::wstring_view name) -> auto {
        return (r / dirs::kInstall / name).wstring();
    };

    cma::cfg::cap::ReInstall();
    auto user_ini = ReadFileInString(user_gen(L"check_mk.ini").c_str());
    auto root_ini = ReadFileInString(root_gen(L"check_mk.ini").c_str());
    auto bakery = cma::tools::ReadFileInString(
        (u / dirs::kBakery / files::kBakeryYmlFile).wstring().c_str());
    auto user_cap_size = fs::file_size(user_gen(L"plugins.cap").c_str());
    auto root_cap_size = fs::file_size(root_gen(L"plugins.cap").c_str());
    auto user_dat = ReadFileInString(user_gen(L"checkmk.dat").c_str());
    auto root_dat = ReadFileInString(root_gen(L"checkmk.dat").c_str());
    ASSERT_TRUE(user_ini);
    ASSERT_EQ(user_cap_size, root_cap_size);
    ASSERT_TRUE(user_dat);
    ASSERT_TRUE(bakery);
    EXPECT_TRUE(user_dat == root_dat);
    EXPECT_TRUE(user_ini == root_ini);
    auto table = SplitString(bakery.value(), "\r\n");
    EXPECT_EQ(table[3], "ps:");

    // now damage files
    auto destroy_file = [](fs::path f) {
        std::ofstream ofs(f, std::ios::binary);

        if (ofs) {
            ofs << "";
        }
    };

    destroy_file(user_gen(L"check_mk.ini"));
    destroy_file(user_gen(L"plugins.cap"));
    destroy_file(user_gen(L"checkmk.dat"));
    destroy_file(u / dirs::kBakery / files::kBakeryYmlFile);
    cma::cfg::cap::ReInstall();

    user_ini = ReadFileInString(user_gen(L"check_mk.ini").c_str());
    bakery = cma::tools::ReadFileInString(
        (u / dirs::kBakery / files::kBakeryYmlFile).wstring().c_str());
    user_cap_size = fs::file_size(user_gen(L"plugins.cap").c_str());
    user_dat = ReadFileInString(user_gen(L"checkmk.dat").c_str());
    ASSERT_TRUE(user_ini);
    ASSERT_EQ(user_cap_size, root_cap_size);
    ASSERT_TRUE(user_dat);
    EXPECT_TRUE(user_dat == root_dat);
    EXPECT_TRUE(user_ini == root_ini);
    table = SplitString(bakery.value(), "\r\n");
    EXPECT_EQ(table[3], "ps:");
}

}  // namespace cma::cfg::cap
