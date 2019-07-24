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
        EXPECT_NO_THROW(res = InstallFileAsCopy(L"", L"", L""));  //
        EXPECT_FALSE(res);

        EXPECT_NO_THROW(res = InstallFileAsCopy(L"sdf", L"c:\\", L"c:\\"));  //
        EXPECT_TRUE(res);

        EXPECT_NO_THROW(
            res = InstallFileAsCopy(L":\\\\wefewfw", L"sssssssss", L"scc"));  //
        EXPECT_FALSE(res);
    }

    // absent source
    {
        tst::ConstructFile(target_file, "1");
        EXPECT_TRUE(InstallFileAsCopy(file_name, target.wstring(),
                                      source.wstring()));  //
        ASSERT_FALSE(fs::exists(target_file, ec)) << "must be removed";
    }

    // target presented
    {
        tst::ConstructFile(source_file, "2");
        EXPECT_TRUE(InstallFileAsCopy(file_name, target.wstring(),
                                      source.wstring()));  //
        EXPECT_TRUE(fs::exists(target_file, ec)) << "must be presented";
    }
}

TEST(CapTest, PackagedAgent) {
    namespace fs = std::filesystem;

    // check we have code compatible with instlalation
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
    std::error_code ec;
    std::wstring names[] = {GetUserPluginsDir() + L"\\windows_if.ps1",
                            GetUserPluginsDir() + L"\\mk_inventory.vbs"};
    namespace fs = std::filesystem;
    fs::path p = GetUserPluginsDir();
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
    }
}

TEST(CapTest, CheckRemove) {
    std::error_code ec;
    std::wstring names[] = {GetUserPluginsDir() + L"\\windows_if.ps1",
                            GetUserPluginsDir() + L"\\mk_inventory.vbs"};
    namespace fs = std::filesystem;
    fs::path p = GetUserPluginsDir();
    auto f_string = p.lexically_normal().wstring();
    ASSERT_TRUE(f_string.find(L"ProgramData\\checkmk\\agent\\plugins"));
    for (auto& name : names) {
        EXPECT_TRUE(fs::exists(name, ec));
    }

    fs::path cap = cma::cfg::GetUserDir();
    cap /= "plugins.test.cap";
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

}  // namespace cma::cfg::cap
