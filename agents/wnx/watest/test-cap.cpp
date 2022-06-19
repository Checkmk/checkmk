// test-cap.cpp:
// Installation of cap files

#include "pch.h"

#include <filesystem>

#include "cap.h"
#include "cfg.h"
#include "cma_core.h"
#include "common/yaml.h"
#include "lwa/types.h"
#include "read_file.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"

namespace fs = std::filesystem;
using namespace std::chrono_literals;

namespace cma::cfg::cap {

TEST(CapTest, NeedReinstallNoThrow) {
    EXPECT_NO_THROW(NeedReinstall("", ""));
    EXPECT_NO_THROW(NeedReinstall("wdwd::::", "\\acfefefvefvwefwegf"));
}

TEST(CapTest, InstallFileAsCopyNoThrow) {
    // absent source and target
    bool res = true;
    EXPECT_NO_THROW(res = InstallFileAsCopy(L"", L"", L"", Mode::normal));
    EXPECT_FALSE(res);

    EXPECT_NO_THROW(
        res = InstallFileAsCopy(L"sdf", L"c:\\", L"c:\\", Mode::normal));
    EXPECT_TRUE(res);

    EXPECT_NO_THROW(res = InstallFileAsCopy(L":\\\\wefewfw", L"sssssssss",
                                            L"scc", Mode::normal));
    EXPECT_FALSE(res);
}

/// \brief Keeps temporary folder and pair of file names and dirs
class CapTestFixture : public ::testing::Test {
public:
    static constexpr std::string_view name() { return "a.txt"; };
    void SetUp() override {}

    fs::path source() const { return source_dir() / name(); }
    fs::path target() const { return target_dir() / name(); }

    fs::path source_dir() const { return temp.in(); }
    fs::path target_dir() const { return temp.out(); }

private:
    tst::TempDirPair temp{
        ::testing::UnitTest::GetInstance()->current_test_info()->name()};
};

TEST_F(CapTestFixture, CheckAreFilesSame) {
    // source without target
    tst::CreateTextFile(source(), "abcde0");
    tst::CreateTextFile(target(), "abcde1");

    EXPECT_FALSE(cma::tools::AreFilesSame(source(), target()));
    EXPECT_TRUE(NeedReinstall(target(), source()));
}

TEST_F(CapTestFixture, ReinstallNoSource) {
    // absent source and target
    EXPECT_FALSE(NeedReinstall(target(), source()));  //

    // absent source
    tst::CreateTextFile(target(), "a");
    EXPECT_FALSE(NeedReinstall(target(), source()));
}

TEST_F(CapTestFixture, ReinstallWithSource) {
    // source without target
    tst::CreateTextFile(source(), "a");
    EXPECT_TRUE(NeedReinstall(target(), source()));

    // target is newer than source
    tst::CreateTextFile(target(), "a");
    EXPECT_FALSE(NeedReinstall(target(), source()));

    // source is newer than target
    auto target_ts{fs::last_write_time(target())};
    fs::last_write_time(source(), target_ts + 10ms);
    EXPECT_TRUE(NeedReinstall(target(), source()));

    // source is older than target, but content is not the same
    fs::last_write_time(target(), target_ts + 50ms);
    EXPECT_TRUE(NeedReinstall(source(), target()));
}

TEST_F(CapTestFixture, InstallFileAsCopy) {
    // absent source
    tst::CreateTextFile(target(), "1");
    EXPECT_TRUE(InstallFileAsCopy(wtools::ConvertToUTF16(name()),
                                  target_dir().wstring(),
                                  source_dir().wstring(),
                                  Mode::normal));  //
    ASSERT_FALSE(fs::exists(target())) << "must be removed";

    // target presented
    tst::CreateTextFile(source(), "2");
    EXPECT_TRUE(InstallFileAsCopy(wtools::ConvertToUTF16(name()),
                                  target_dir().wstring(),
                                  source_dir().wstring(),
                                  Mode::normal));  //
    EXPECT_TRUE(fs::exists(target())) << "must be presented";
}

static bool ValidateInstallYml(const std::filesystem::path &file) {
    auto yml = YAML::LoadFile(wtools::ToUtf8(file.wstring()));
    if (!yml.IsDefined() || !yml.IsMap()) return false;
    try {
        return yml[groups::kGlobal][vars::kInstall].as<bool>() &&
               yml[groups::kGlobal][vars::kEnabled].as<bool>();
    } catch (const std::exception &e) {
        XLOG::l("exception during tests", e.what());
        return false;
    }
}

/// \brief Keeps temporary folder and pair of file names and dirs
class CapTestYamlFixture : public ::testing::Test {
public:
    static constexpr std::string_view name() { return files::kInstallYmlFileA; }
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        fs::create_directories(temp_fs_->root() / dirs::kInstall);
        fs::create_directories(temp_fs_->data() / dirs::kUserInstallDir);
    }

    fs::path yml_source() const {
        return temp_fs_->root() / dirs::kInstall / name();
    }
    fs::path yml_target() const {
        return temp_fs_->data() / dirs::kInstall / name();
    }

private:
    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(CapTestYamlFixture, Uninstall) {
    EXPECT_NO_THROW(details::UninstallYaml(GetBakeryFile(), yml_target()));

    // bakery [+] target[-]
    // Uninstall
    // bakery [+] target[-]
    tst::CreateWorkFile(GetBakeryFile(), "b");
    EXPECT_NO_THROW(details::UninstallYaml(GetBakeryFile(), yml_target()));
    EXPECT_TRUE(fs::exists(GetBakeryFile())) << "if";

    // bakery [+] target[+]
    // Uninstall
    // bakery [-] target[-]
    tst::CreateWorkFile(yml_target(), "b");
    EXPECT_NO_THROW(details::UninstallYaml(GetBakeryFile(), yml_target()));
    EXPECT_FALSE(fs::exists(GetBakeryFile())) << "if";
    EXPECT_FALSE(fs::exists(yml_target())) << "if";
}

TEST_F(CapTestYamlFixture, Install) {
    // exists source yml
    tst::CreateWorkFile(yml_source(), "s");
    EXPECT_NO_THROW(
        details::InstallYaml(GetBakeryFile(), yml_target(), yml_source()));
    EXPECT_TRUE(fs::exists(yml_target()));
    EXPECT_TRUE(fs::exists(GetBakeryFile()));

    // simulate MSI without yml
    fs::remove(yml_source());
    EXPECT_NO_THROW(
        details::InstallYaml(GetBakeryFile(), yml_target(), yml_source()));
    EXPECT_TRUE(fs::exists(yml_target())) << "should exist";
    EXPECT_TRUE(fs::exists(GetBakeryFile())) << "should exist";
}

TEST_F(CapTestYamlFixture, ReInstall) {
    auto yml_base =
        tst::MakePathToConfigTestFiles() / "check_mk.wato.install.yml";
    ASSERT_TRUE(fs::exists(yml_base));

    auto yml_bakery = GetBakeryFile();

    // absent source and target, nothing done
    EXPECT_NO_THROW(ReinstallYaml("", "", ""));
    EXPECT_NO_THROW(ReinstallYaml("a", ":\\\\wefewfw", "sssssssss"));
    EXPECT_FALSE(ReinstallYaml(yml_bakery, yml_target(), yml_source()));
    EXPECT_FALSE(fs::exists(yml_bakery)) << "must be absent";
    EXPECT_FALSE(fs::exists(yml_target())) << "must be absent";

    // target presented: everything is removed
    // fs::copy_file(yml_base, yml_source());
    tst::CreateWorkFile(yml_target(), "brr1");
    tst::CreateWorkFile(yml_bakery, "brr2");
    EXPECT_FALSE(ReinstallYaml(yml_bakery, yml_target(), yml_source()));
    EXPECT_FALSE(fs::exists(yml_bakery));
    EXPECT_FALSE(fs::exists(yml_target()));

    // target and source presented
    fs::copy_file(yml_base, yml_source());
    tst::CreateWorkFile(yml_target(), "brr1");
    tst::CreateWorkFile(yml_bakery, "brr2");
    EXPECT_TRUE(ReinstallYaml(yml_bakery, yml_target(), yml_source()));
    EXPECT_TRUE(fs::exists(yml_bakery)) << "must be presented";
    EXPECT_TRUE(fs::exists(yml_target())) << "must be presented";
    EXPECT_TRUE(ValidateInstallYml(yml_bakery));
    EXPECT_TRUE(ValidateInstallYml(yml_source()));
}

TEST(CapTest, InstallCap) {
    auto temp_fs{tst::TempCfgFs::Create()};
    auto [source, target] = tst::CreateInOut();
    std::error_code ec;

    std::string cap_name = "plugins.cap";
    fs::path cap_base = tst::MakePathToCapTestFiles() / "plugins.test.cap";
    fs::path cap_null = tst::MakePathToCapTestFiles() / "plugins_null.test.cap";
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
        tst::CreateTextFile(plugin1, "1");
        tst::CreateTextFile(plugin2, "2");
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
    auto temp_fs{tst::TempCfgFs::Create()};
    std::string name = "a/b.txt";
    auto out = ProcessPluginPath(name);
    fs::path expected_path = cma::cfg::GetUserDir() + L"\\a\\b.txt";
    EXPECT_EQ(out, expected_path.lexically_normal());
}

TEST(CapTest, IsAllowedToKill) {
    using namespace cma::cfg;
    auto temp_fs{tst::TempCfgFs::Create()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));

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

    auto work = tst::MakeTempFolderInTempPath(wtools::ConvertToUTF16(
        ::testing::UnitTest::GetInstance()->current_test_info()->name()));
    fs::create_directories(work);

    fs::path ping(R"(c:\windows\system32\ping.exe)");
    if (!fs::exists(ping)) GTEST_SKIP() << "there is no ping.exe";
    fs::path cmk_test_ping = work / "cmk-update-aGent.exe";
    wtools::KillProcessFully(cmk_test_ping.filename().wstring(), 9);
    cma::tools::sleep(200ms);
    ASSERT_TRUE(fs::copy_file(ping, cmk_test_ping,
                              fs::copy_options::overwrite_existing));
    ASSERT_TRUE(
        tools::RunDetachedCommand(cmk_test_ping.u8string() + " -t 8.8.8.8"));
    cma::tools::sleep(200ms);
    std::vector<char> buf = {'_', '_'};
    ASSERT_FALSE(StoreFile(cmk_test_ping, buf));
    ASSERT_TRUE(StoreFileAgressive(cmk_test_ping, buf, 1));
    ASSERT_TRUE(fs::copy_file(ping, cmk_test_ping,
                              fs::copy_options::overwrite_existing));
    ASSERT_TRUE(
        tools::RunDetachedCommand(cmk_test_ping.u8string() + " -t 8.8.8.8"));
    cma::tools::sleep(200ms);

    std::error_code ec;
    fs::remove(cmk_test_ping, ec);
    ASSERT_FALSE(StoreFile(cmk_test_ping, buf));
    ASSERT_TRUE(StoreFileAgressive(cmk_test_ping, buf, 1));
    wtools::KillProcessFully(cmk_test_ping.filename().wstring(), 9);
}

class CapTestProcessFixture : public ::testing::Test {
public:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        names_[0] = GetUserPluginsDir() + L"\\windows_if.ps1";
        names_[1] = GetUserPluginsDir() + L"\\mk_inventory.vbs";
    }

    const std::array<std::wstring, 2> &names() const { return names_; };

    void makeFilesInPlugins() {
        fs::create_directories(GetUserPluginsDir());
        ASSERT_TRUE(temp_fs_->createDataFile(
            fs::path{"plugins"} / "windows_if.ps1", "1"));
        ASSERT_TRUE(temp_fs_->createDataFile(
            fs::path{"plugins"} / "mk_inventory.vbs", "1"));
    }

private:
    std::array<std::wstring, 2> names_;

    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(CapTestProcessFixture, ValidFile) {
    auto cap = tst::MakePathToCapTestFiles() / "plugins.test.cap";

    std::vector<std::wstring> files;
    EXPECT_TRUE(Process(cap.u8string(), ProcMode::list, files));
    ASSERT_EQ(files.size(), 2);
    for (int i = 0; i < 2; ++i) {
        EXPECT_EQ(files[i], names()[i])
            << "Mismatch " << files[i] << " to " << names()[i];
    }
}

TEST_F(CapTestProcessFixture, EmptyFile) {
    auto cap = tst::MakePathToCapTestFiles() / "plugins_null.test.cap";

    std::vector<std::wstring> files;
    auto ret = Process(cap.u8string(), ProcMode::list, files);
    EXPECT_TRUE(ret);
    EXPECT_EQ(files.size(), 0);
}

TEST_F(CapTestProcessFixture, Install) {
    fs::create_directories(GetUserPluginsDir());
    auto cap = tst::MakePathToCapTestFiles() / "plugins.test.cap";

    std::vector<std::wstring> files;
    EXPECT_TRUE(Process(cap.u8string(), ProcMode::install, files));
    ASSERT_EQ(files.size(), 2);
    for (int i = 0; i < 2; ++i) {
        EXPECT_EQ(files[i], names()[i])
            << "Mismatch " << files[i] << " to " << names()[i];
    }
}

TEST_F(CapTestProcessFixture, Remove) {
    auto cap = tst::MakePathToCapTestFiles() / "plugins.test.cap";

    makeFilesInPlugins();

    std::vector<std::wstring> files;
    EXPECT_TRUE(Process(cap.u8string(), ProcMode::remove, files));

    ASSERT_EQ(files.size(), 2);
    for (int i = 0; i < 2; ++i) {
        EXPECT_EQ(files[i], names()[i])
            << "Mismatch " << files[i] << " to " << names()[i];
        EXPECT_FALSE(fs::exists(names()[i]));
    }
}

TEST_F(CapTestProcessFixture, BadFiles) {
    using namespace std::string_literals;

    XLOG::l.i("Next log output should be crit. This is SUCCESS");
    std::array<std::pair<std::string, int>, 3> data{
        {{"plugins_invalid.test.cap"s, 1},
         {"plugins_long.test.cap"s, 2},
         {"plugins_short.test.cap"s, 1}}

    };

    for (auto const &test : data) {
        auto bad_cap = tst::MakePathToCapTestFiles() / test.first;
        std::vector<std::wstring> results;
        EXPECT_FALSE(Process(bad_cap.u8string(), ProcMode::list, results));
        ASSERT_EQ(results.size(), test.second)
            << "this file is invalid, but first file should be ok: "
            << test.first;
    }
}

namespace {
fs::path CreateInvalidCap() {
    auto file_name = tst::GetTempDir() / "invalid.cap";
    std::fstream file;
    uint8_t name_len = 12;
    constexpr char name[] = "123456789012";
    file.open(file_name, std::ios::trunc | std::ios::binary | std::ios::out);
    file.write(reinterpret_cast<const char *>(&name_len), sizeof(name_len));
    file.write(name, name_len);
    uint32_t len = 123000;
    file.write(reinterpret_cast<const char *>(&len), sizeof(len));
    file.write(name, name_len);
    return file_name;
}
}  // namespace
TEST(CapTest, InvalidFile) {
    auto file_name = CreateInvalidCap();
    ASSERT_TRUE(fs::exists(file_name));
    std::vector<std::wstring> files;
    EXPECT_FALSE(Process(file_name.u8string(), ProcMode::list, files));
}

TEST(CapTest, GetExampleYmlNames) {
    auto temp_fs{tst::TempCfgFs::Create()};
    auto expected_example_yml = fs::path{GetUserDir()} / files::kUserYmlFile;
    expected_example_yml.replace_extension("example.yml");
    auto expected_source_yml =
        fs::path{GetRootInstallDir()} / files::kUserYmlFile;

    auto [target_example_yml, source_yml] = GetExampleYmlNames();
    EXPECT_EQ(target_example_yml, expected_example_yml);
    EXPECT_EQ(source_yml, expected_source_yml);
}

// This is complicated test, rather Functional/Business
// We are checking three situation
// Build  check_mk.install.yml is present, but not installed
// Build  check_mk.install.yml is present and installed
TEST(CapTest, ReInstallRestoreIntegration) {
    using namespace cma::tools;
    enum class Mode { build, wato };
    for (auto mode : {Mode::build, Mode::wato}) {
        auto test_fs = tst::TempCfgFs::Create();

        ASSERT_TRUE(test_fs->loadFactoryConfig());

        auto r = test_fs->root();
        auto u = test_fs->data();

        fs::path cap_base = tst::MakePathToCapTestFiles() / "plugins.test.cap";
        fs::path yml_b_base =
            tst::MakePathToConfigTestFiles() / "check_mk.build.install.yml";
        fs::path yml_w_base =
            tst::MakePathToConfigTestFiles() / "check_mk.wato.install.yml";

        std::error_code ec;
        try {
            // Prepare installed files
            fs::create_directory(r / dirs::kInstall);
            fs::copy_file(cap_base, r / dirs::kInstall / "plugins.cap");
            tst::CreateWorkFile(r / dirs::kInstall / "checkmk.dat", "this");

            if (mode == Mode::build)
                fs::copy_file(yml_b_base,
                              r / dirs::kInstall / files::kInstallYmlFileA);
            if (mode == Mode::wato)
                fs::copy_file(yml_w_base,
                              r / dirs::kInstall / files::kInstallYmlFileA);

        } catch (const std::exception &e) {
            ASSERT_TRUE(false) << "can't create file data exception is "
                               << e.what() << "Mode " << static_cast<int>(mode);
        }

        // change folders
        auto user_gen = [u](const std::wstring_view name) -> auto {
            return (u / dirs::kInstall / name).wstring();
        };

        auto root_gen = [r](const std::wstring_view name) -> auto {
            return (r / dirs::kInstall / name).wstring();
        };

        // Main Function
        EXPECT_TRUE(cma::cfg::cap::ReInstall());

        auto bakery = cma::tools::ReadFileInString(
            (u / dirs::kBakery / files::kBakeryYmlFile).wstring().c_str());
        auto user_cap_size = fs::file_size(user_gen(L"plugins.cap").c_str());
        auto root_cap_size = fs::file_size(root_gen(L"plugins.cap").c_str());
        auto user_dat = ReadFileInString(user_gen(L"checkmk.dat").c_str());
        auto root_dat = ReadFileInString(root_gen(L"checkmk.dat").c_str());
        ASSERT_EQ(user_cap_size, root_cap_size);
        ASSERT_TRUE(user_dat);
        ASSERT_TRUE(bakery.has_value() == (mode == Mode::wato));
        EXPECT_TRUE(user_dat == root_dat);

        // bakery check
        if (mode == Mode::wato) {
            auto y = YAML::Load(*bakery);
            EXPECT_NO_THROW(y["global"]["wato"].as<bool>());
            EXPECT_TRUE(y["global"]["wato"].as<bool>());
        } else {
            ASSERT_FALSE(bakery);
        }

        // now damage files
        auto destroy_file = [](fs::path f) {
            std::ofstream ofs(f, std::ios::binary);

            if (ofs) {
                ofs << "";
            }
        };

        destroy_file(user_gen(files::kInstallYmlFileW));
        destroy_file(user_gen(L"plugins.cap"));
        destroy_file(user_gen(L"checkmk.dat"));
        destroy_file(u / dirs::kBakery / files::kBakeryYmlFile);

        // main Function again
        EXPECT_TRUE(cma::cfg::cap::ReInstall());

        bakery = cma::tools::ReadFileInString(
            (u / dirs::kBakery / files::kBakeryYmlFile).wstring().c_str());
        user_cap_size = fs::file_size(user_gen(L"plugins.cap").c_str());
        user_dat = ReadFileInString(user_gen(L"checkmk.dat").c_str());
        ASSERT_EQ(user_cap_size, root_cap_size);
        ASSERT_TRUE(user_dat);
        EXPECT_TRUE(user_dat == root_dat);

        // bakery check
        if (mode == Mode::wato) {
            auto y = YAML::Load(*bakery);
            EXPECT_NO_THROW(y["global"]["wato"].as<bool>());
            EXPECT_TRUE(y["global"]["wato"].as<bool>());
        } else {
            ASSERT_FALSE(bakery);
        }
    }
}

}  // namespace cma::cfg::cap
