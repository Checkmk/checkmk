//
// modules tests
//
//
#include "pch.h"

#include <fmt/format.h>
#include <shellapi.h>

#include <filesystem>
#include <iterator>

#include "cfg.h"
#include "modules.h"
#include "test_tools.h"
#include "zip.h"

namespace cma::tools {
template <typename T, typename = void>
struct is_iterable : std::false_type {};

// this gets used only when we can call std::begin() and std::end() on that type
template <typename T>
struct is_iterable<T, std::void_t<decltype(std::begin(std::declval<T>())),
                                  decltype(std::end(std::declval<T>()))>>
    : std::true_type {};

// Here is a helper:
template <typename T>
constexpr bool is_iterable_v = is_iterable<T>::value;
}  // namespace cma::tools

namespace cma::cfg::modules {

template <typename T>
bool Compare(const T& t, const T& v) {
    static_assert(cma::tools::is_iterable<T>::value);
    if (t.size() != v.size()) return false;

    return std::equal(t.begin(), t.end(), v.begin());
}

TEST(ModuleCommander, CheckSystemAuto) {
    namespace fs = std::filesystem;
    using namespace cma::cfg;

    cma::OnStartTest();
    ON_OUT_OF_SCOPE(cma::OnStartTest());

    auto sys_exts = ModuleCommander::GetSystemExtensions();
    ASSERT_TRUE(sys_exts.size() == 1);
    ASSERT_TRUE(sys_exts[0].first == "python");
    ASSERT_TRUE(sys_exts[0].second == ".py");

    std::string base_1 =
        "globals:\n"
        "  enabled: yes\n"
        "modules:\n"
        "  enabled: yes\n"
        "  table:\n"
        "    - name: 'aaa'\n"
        "      exts: ['.checkmk.py','.py']\n"
        "      exec: 'thos.exe {}'\n";
    {
        ModuleCommander mc;
        auto node = YAML::Load(base_1);
        mc.readConfig(node);
        ASSERT_TRUE(mc.getExtensions().size() == 2);
        EXPECT_TRUE(mc.isModuleScript("z.py"));

        node["modules"]["python"] = "auto";
        mc.readConfig(node);
        ASSERT_TRUE(mc.getExtensions().size() == 2);
        EXPECT_TRUE(mc.isModuleScript("z.py"));
    }

    {
        ModuleCommander mc;
        auto node = YAML::Load(base_1);
        node["modules"]["python"] = "system";
        mc.readConfig(node);
        ASSERT_TRUE(mc.getExtensions().size() == 1);
        EXPECT_FALSE(mc.isModuleScript("z.py"));
    }
}

TEST(ModulesTest, Internal) {
    Module m;
    EXPECT_FALSE(m.valid());
    EXPECT_TRUE(m.exec().empty());
    EXPECT_TRUE(m.exts().empty());
    EXPECT_TRUE(m.name().empty());
    EXPECT_TRUE(m.exec_.empty());
    EXPECT_TRUE(m.exts_.empty());
    EXPECT_TRUE(m.name_.empty());
    EXPECT_TRUE(m.bin_.empty());
    EXPECT_TRUE(m.zip_.empty());

    m.exec_ = L"a";
    m.exts_.emplace_back(".v");
    m.name_ = "z";
    EXPECT_EQ(m.exec(), L"a");
    EXPECT_EQ(m.name(), "z");
    EXPECT_TRUE(Compare(m.exts(), {".v"}));
    EXPECT_TRUE(m.valid());

    m.bin_ = "z";
    EXPECT_EQ(m.bin(), "z");

    m.zip_ = "z";
    EXPECT_EQ(m.zip(), "z");

    std::filesystem::path x = GetUserDir();
    EXPECT_EQ(m.buildCommandLine("q.v"), (x / m.exec()).wstring());
    EXPECT_TRUE(m.buildCommandLine("q.x").empty()) << "invalid extension";

    m.exec_ = L"a {}";
    EXPECT_EQ(m.buildCommandLine("q.v"), x.wstring() + L"\\a q.v");

    // reset test
    m.reset();
    EXPECT_FALSE(m.valid());
    EXPECT_TRUE(m.exec().empty());
    EXPECT_TRUE(m.exts().empty());
    EXPECT_TRUE(m.name().empty());
    EXPECT_TRUE(m.zip().empty());
    EXPECT_TRUE(m.bin().empty());
}

struct TestSet {
    std::string name;
    std::string exts;
    std::string exec;
    std::string dir;
};

TEST(ModulesTest, Loader) {
    TestSet bad_sets[] = {
        //
        {{}, {}, {}, {}},
        {{""}, {"[e1]"}, {"x"}, {""}},
        {{}, {"[e1]"}, {"x"}, {"dir: m\\{}"}},
        //
    };
    TestSet good_sets[] = {
        //
        {"the-1.0", "[.e1, .e2, .e3]", "x", "dir: modules\\{}"},  // full
        {"the-1.0", "[.e1]", "x", "dir: "},                       // empty dir
        {"the-1.0", "[.e1]", "x", ""},                            // empty dir
        //
    };

    constexpr std::string_view base =
        "name: {}\n"
        "exts: {}\n"
        "exec: {}\n"
        "{}\n";

    for (auto s : good_sets) {
        Module m;
        auto text = fmt::format(base, s.name, s.exts, s.exec, s.dir);
        auto node = YAML::Load(text);
        EXPECT_TRUE(m.loadFrom(node));
        EXPECT_TRUE(m.valid());
        EXPECT_EQ(m.name(), s.name);
        auto arr = cma::cfg::GetArray<std::string>(YAML::Load(s.exts));
        EXPECT_TRUE(Compare(m.exts(), arr));
        EXPECT_EQ(m.exec(), wtools::ConvertToUTF16(s.exec));
        if (s.dir.size() <= 5)
            EXPECT_EQ(m.dir(), fmt::format(defaults::kModulesDir, m.name()));
        else
            EXPECT_EQ(m.dir(), fmt::format(s.dir.c_str() + 5, m.name()));
    }

    {
        Module m;
        auto s = good_sets[0];
        auto text = fmt::format(base, s.name, s.exts, s.exec, s.dir);
        auto node = YAML::Load(text);
        EXPECT_TRUE(m.loadFrom(node));
        auto arr = cma::cfg::GetArray<std::string>(YAML::Load(s.exts));
        EXPECT_TRUE(Compare(m.exts(), arr));
        m.removeExtension(".e2");
        EXPECT_EQ(m.exts().size(), 2);
        EXPECT_EQ(m.exts()[0], ".e1");
        EXPECT_EQ(m.exts()[1], ".e3");
        m.removeExtension(".e3");
        EXPECT_EQ(m.exts().size(), 1);
        EXPECT_EQ(m.exts()[0], ".e1");
    }

    for (auto s : bad_sets) {
        Module m;
        auto text = fmt::format(base, s.name, s.exts, s.exec, s.dir);
        auto node = YAML::Load(text);
        EXPECT_FALSE(m.loadFrom(node));
        EXPECT_FALSE(m.valid());
        EXPECT_TRUE(m.exec().empty());
        EXPECT_TRUE(m.exts().empty());
        EXPECT_TRUE(m.name().empty());
        EXPECT_TRUE(m.dir().empty());
    }
}

TEST(ModulesTest, IsMyScript) {
    namespace fs = std::filesystem;

    Module m;
    EXPECT_FALSE(m.isMyScript("z"));
    EXPECT_FALSE(m.isMyScript("z.ix"));
    m.exts_.emplace_back(".ix");
    EXPECT_TRUE(m.isMyScript("z.ix"));
    EXPECT_TRUE(m.isMyScript("z.m.ix"));
    EXPECT_FALSE(m.isMyScript("z"));
    m.exts_.emplace_back(".vv");
    EXPECT_TRUE(m.isMyScript("z.vv"));
    EXPECT_TRUE(m.isMyScript("z.ix"));
    EXPECT_TRUE(m.isMyScript("z.m.ix"));
    EXPECT_FALSE(m.isMyScript("z"));
    m.exts_.emplace_back("vvv");
    EXPECT_FALSE(m.isMyScript("z.vvv"));
    m.exts_.emplace_back(".");
    EXPECT_TRUE(m.isMyScript("z"));
}

TEST(ModulesTest, TableLoader) {
    std::string work_set[7] = {
        "the",  "['.a', '.b']", "x",           //
        "the2", "['.a']",       "x2", "m\\{}"  //
    };

    constexpr std::string_view base =
        "modules:\n"
        "  enabled: {0}\n"
        "  table:\n"
        "    - name: {1}\n"           // valid
        "      exts: {2}\n"           //
        "      exec: {3}\n"           //
        "    - name: {1}\n"           // duplicated
        "      exts: {2}\n"           //
        "      exec: {3}\n"           //
        "    - name: \n"              // invalid
        "      exts: ['.a', '.b']\n"  //
        "      exec: z\n"             //
        "    - name: {4}\n"           // valid
        "      exts: {5}\n"           //
        "      exec: {6}\n"           //
        "      dir: {7}\n";           //

    {
        Module m;
        {
            auto text =
                fmt::format(base, "No", work_set[0], work_set[1], work_set[2],
                            work_set[3], work_set[4], work_set[5], work_set[6]);
            auto config = YAML::Load(text);
            auto modules = LoadFromConfig(config);
            ASSERT_TRUE(modules.empty());
        }
        {
            auto text =
                fmt::format(base, "Yes", work_set[0], work_set[1], work_set[2],
                            work_set[3], work_set[4], work_set[5], work_set[6]);
            auto config = YAML::Load(text);
            auto modules = LoadFromConfig(config);
            ASSERT_EQ(modules.size(), 2);
            EXPECT_EQ(modules[0].name(), "the");
            EXPECT_EQ(modules[1].name(), "the2");
            EXPECT_EQ(modules[0].exec(), L"x");
            EXPECT_EQ(modules[1].exec(), L"x2");
            EXPECT_TRUE(Compare(modules[0].exts(),
                                std::vector<std::string>{".a", ".b"}));
            EXPECT_TRUE(
                Compare(modules[1].exts(), std::vector<std::string>{".a"}));
            EXPECT_EQ(modules[0].dir(), "modules\\the");
            EXPECT_EQ(modules[1].dir(), "m\\the2");
        }
    }
}

TEST(ModuleCommander, ReadConfig) {
    std::string base =
        "modules:\n"
        "  enabled: yes\n"
        "  table:\n"
        "    - name: unzip_test\n"     // valid
        "      exts: ['.test']\n"      //
        "      exec: 'nothing {}'\n"   //
        "    - name: unzip_test2\n"    // valid
        "      exts: ['.test2']\n"     //
        "      exec: 'nothing2 {}'\n"  //
        "      dir:  'plugins'\n";

    ModuleCommander mc;
    auto node = YAML::Load(base);
    mc.readConfig(node);
    ASSERT_TRUE(mc.modules_.size() == 2);
    EXPECT_EQ(mc.modules_[0].name(), "unzip_test");
    EXPECT_EQ(mc.modules_[1].name(), "unzip_test2");
    EXPECT_EQ(mc.modules_[0].exec(), L"nothing {}");
    EXPECT_EQ(mc.modules_[1].exec(), L"nothing2 {}");
    EXPECT_EQ(mc.modules_[0].dir(), "modules\\unzip_test");
    EXPECT_EQ(mc.modules_[1].dir(), "plugins");
}

class ModuleCommanderTest : public ::testing::Test {
protected:
    void SetUp() override {
        cma::OnStartTest();
        tst::SafeCleanTempDir();
    }

    void TearDown() override { tst::SafeCleanTempDir(); }
};

TEST_F(ModuleCommanderTest, PrepareToWork) {
    namespace fs = std::filesystem;
    using namespace cma::cfg;

    fs::path user = tst::CreateDirInTemp(L"user");
    auto modules_dir = user / dirs::kUserModules;
    auto backup_dir = user / dirs::kInstall / dirs::kInstalledModules;
    fs::create_directories(modules_dir);
    fs::create_directories(backup_dir);

    Module m;
    std::string test_1 =
        "name: zz\n"      // valid
        "exts: ['.t']\n"  //
        "exec: 'zz.exe {}'\n";
    ASSERT_TRUE(m.loadFrom(YAML::Load(test_1)));
    ASSERT_TRUE(m.name() == "zz" && m.exec() == L"zz.exe {}");
    EXPECT_FALSE(m.prepareToWork(backup_dir, modules_dir));
    tst::ConstructFile(backup_dir / (m.name() + kExtension.data()), "zip");
    EXPECT_FALSE(m.prepareToWork(backup_dir, modules_dir));
    EXPECT_EQ(m.zip(), backup_dir / "zz.zip");
    EXPECT_TRUE(m.buildCommandLine("x.t").empty());

    fs::create_directories(modules_dir / m.name());
    tst::ConstructFile(modules_dir / m.name() / "zz.exe", "exe");
    EXPECT_TRUE(m.prepareToWork(backup_dir, modules_dir));
    EXPECT_EQ(m.bin(), modules_dir / m.name() / "zz.exe");
    auto expected_location = std::filesystem::path{GetUserDir()} / m.dir();
    EXPECT_EQ(m.buildCommandLine("x.t"),
              expected_location.wstring() + L"\\zz.exe x.t");
    EXPECT_TRUE(m.buildCommandLine("x.tx").empty());
    EXPECT_EQ(m.buildCommandLineForced("x.z"),
              expected_location.wstring() + L"\\zz.exe x.z");
}

TEST_F(ModuleCommanderTest, PrepareToWork2) {
    namespace fs = std::filesystem;
    using namespace cma::cfg;

    fs::path user = tst::CreateDirInTemp(L"user");
    fs::path root = tst::CreateDirInTemp(L"root");
    GetCfg().pushFolders(root, user);
    ON_OUT_OF_SCOPE(GetCfg().popFolders());

    auto modules_dir = user / dirs::kUserModules;
    auto backup_dir = user / dirs::kInstall / dirs::kInstalledModules;
    fs::create_directories(modules_dir);
    fs::create_directories(backup_dir);

    std::string base =
        "modules:\n"
        "  enabled: yes\n"
        "  table:\n"
        "    - name: zz\n"           // valid
        "      exts: ['.t']\n"       //
        "      exec: 'zz.exe {}'\n"  //
        "    - name: qq\n"           // valid
        "      exts: ['.test2']\n"   //
        "      exec: 'nothing2'\n"   //
        "      dir:  'plugins'\n";

    ModuleCommander mc;
    auto node = YAML::Load(base);
    mc.readConfig(node);
    ASSERT_EQ(mc.modules_.size(), 2);

    mc.prepareToWork();
    for (auto& m : mc.modules_) {
        ASSERT_TRUE(m.bin().empty());
        ASSERT_TRUE(m.zip().empty());
    }

    tst::ConstructFile(backup_dir / (mc.modules_[0].name() + kExtension.data()),
                       "zip");
    mc.prepareToWork();
    {
        ASSERT_TRUE(mc.modules_[0].bin().empty());
        ASSERT_FALSE(mc.modules_[0].zip().empty());
        ASSERT_TRUE(mc.modules_[1].bin().empty());
        ASSERT_TRUE(mc.modules_[1].zip().empty());
    }

    fs::create_directories(modules_dir / mc.modules_[0].name());
    tst::ConstructFile(modules_dir / mc.modules_[0].name() / "zz.exe", "exe");
    mc.prepareToWork();
    {
        ASSERT_FALSE(mc.modules_[0].bin().empty());
        ASSERT_FALSE(mc.modules_[0].zip().empty());
        ASSERT_TRUE(mc.modules_[1].bin().empty());
        ASSERT_TRUE(mc.modules_[1].zip().empty());
    }

    EXPECT_TRUE(mc.isModuleScript("cc.t"));
    EXPECT_FALSE(mc.isModuleScript("cc"));
    EXPECT_FALSE(mc.isModuleScript("cc.c"));

    auto expected_location =
        std::filesystem::path{GetUserDir()} / mc.modules_[0].dir();
    EXPECT_EQ(mc.buildCommandLine("x.t"),
              expected_location.wstring() + L"\\zz.exe x.t");
}

TEST_F(ModuleCommanderTest, LowLevelFs) {
    using namespace std::literals;
    namespace fs = std::filesystem;
    fs::path root = cma::cfg::GetTempDir();
    fs::path user = tst::CreateDirInTemp(L"user");

    ModuleCommander::CreateBackupFolder(user);
    auto backup_dir = user / dirs::kInstall / dirs::kInstalledModules;
    ASSERT_TRUE(fs::exists(backup_dir));

    auto mod_file = user / "to_backup";
    tst::ConstructFile(mod_file, "11");

    auto backup_file = backup_dir / "to_backup";
    ASSERT_FALSE(fs::exists(backup_file));
    ASSERT_TRUE(ModuleCommander::BackupModule(mod_file, backup_file));
    ASSERT_TRUE(fs::exists(backup_file));
    {
        // simulate busy
        std::fstream fs;
        fs.open(backup_file, std::ios::in, _SH_DENYRW);
        ASSERT_FALSE(ModuleCommander::BackupModule(mod_file, backup_file));
    }

    auto mod_dir = user / dirs::kUserModules / "zis";
    ModuleCommander::PrepareCleanTargetDir(mod_dir);
    ASSERT_TRUE(fs::exists(mod_dir));
    auto dummy_file = mod_dir / "t.txt";
    tst::ConstructFile(dummy_file, "aaaaa");
    ASSERT_TRUE(fs::exists(dummy_file));
    ModuleCommander::PrepareCleanTargetDir(mod_dir);
    ASSERT_TRUE(fs::exists(mod_dir));
    ASSERT_FALSE(fs::exists(dummy_file));
}

TEST_F(ModuleCommanderTest, FindModules) {
    using namespace std::literals;
    namespace fs = std::filesystem;
    fs::path root = cma::cfg::GetTempDir();
    fs::path install = tst::CreateDirInTemp(dirs::kInstall);

    std::string base =
        "modules:\n"
        "  enabled: yes\n"
        "  table:\n"
        "    - name: real_module_module\n"      // valid
        "      exts: ['.test']\n"               //
        "      exec: 'nothing {}'\n"            //
        "    - name: real_module_module2\n"     // valid
        "      exts: ['.test2', 'test3.tt']\n"  //
        "      exec: 'nothing2 {}'\n"           //
        "      dir:  'plugins'\n";

    ModuleCommander mc;
    EXPECT_FALSE(mc.isBelongsToModules("c:\\windows\\real_module_module.zip"));
    auto node = YAML::Load(base);
    mc.readConfig(node);
    ASSERT_EQ(mc.findModuleFiles(root), 0);
    EXPECT_TRUE(mc.files_.empty());
    tst::ConstructFile(install / "not_module", "z");
    ASSERT_EQ(mc.findModuleFiles(root), 0);
    tst::ConstructFile(install / ("null_module_module"s + kExtension.data()),
                       "");
    ASSERT_EQ(mc.findModuleFiles(root), 0);

    EXPECT_EQ(mc.getExtensions(),
              std::vector<std::string>({".test"s, ".test2"s, "test3.tt"s}));

    tst::ConstructFile(install / ("real_module_module"s + kExtension.data()),
                       "zip");
    ASSERT_EQ(mc.findModuleFiles(root), 1);

    tst::ConstructFile(install / ("real_module_module2"s + kExtension.data()),
                       "zip");
    ASSERT_EQ(mc.findModuleFiles(root), 2);

    // check that name are correctly found in modules list
    EXPECT_FALSE(mc.isBelongsToModules("c:\\windows\\real_module_module"));
    EXPECT_FALSE(mc.isBelongsToModules("c:\\windows\\real_module_module.zi"));
    EXPECT_TRUE(mc.isBelongsToModules("c:\\windows\\real_module_module.zip"));
    EXPECT_TRUE(mc.isBelongsToModules("c:\\windows\\real_module_module2.zip"));

    EXPECT_FALSE(mc.isBelongsToModules(""));
}

TEST_F(ModuleCommanderTest, Internal) {
    using namespace std::literals;
    namespace fs = std::filesystem;
    fs::path user_dir = cma::cfg::GetUserDir();
    fs::path user = cma::cfg::GetTempDir();
    fs::path modules = ModuleCommander::GetModInstall(user);

    ModuleCommander mc;
    auto dir = user / dirs::kUserModules / "tst";
    EXPECT_FALSE(mc.CreateFileForTargetDir("c:\\windows", modules));
    EXPECT_FALSE(mc.CreateFileForTargetDir(modules / "tst", "c:\\windows"));
    EXPECT_TRUE(mc.CreateFileForTargetDir(modules / "tst", modules));

    auto result =
        cma::tools::ReadFileInString((dir / kTargetDir).u8string().c_str());
    ASSERT_EQ(result, modules.u8string());

    // simulate file creation from unzip
    fs::create_directories(modules / "doc");
    tst::CreateWorkFile(modules / "test.txt", "z");
    // simulate file existing before(should stay)

    // uninstall by directory content
    tst::CreateWorkFile(modules / "test_left.txt", "z");

    // check results
    EXPECT_TRUE(fs::exists(modules / "doc"));
    EXPECT_TRUE(fs::exists(modules / "test.txt"));
    EXPECT_TRUE(fs::exists(modules / "test_left.txt"));

    EXPECT_TRUE(mc.RemoveContentByTargetDir({}, modules / "tst"));
    EXPECT_FALSE(mc.RemoveContentByTargetDir({L"doc"}, modules / "t"));

    EXPECT_FALSE(mc.RemoveContentByTargetDir({L"doc", L"test.txt"}, {}));

    EXPECT_TRUE(
        mc.RemoveContentByTargetDir({L"doc", L"test.txt"}, modules / "tst"));
    EXPECT_FALSE(fs::exists(modules / "doc"));
    EXPECT_FALSE(fs::exists(modules / "test.txt"));
    EXPECT_TRUE(fs::exists(modules / "test_left.txt"));
}

TEST_F(ModuleCommanderTest, InstallModules) {
    using namespace std::literals;
    namespace fs = std::filesystem;
    fs::path user_dir = cma::cfg::GetUserDir();

    auto zip_file = user_dir / tst::zip_to_test;
    ASSERT_TRUE(fs::exists(zip_file))
        << "Please make '" << tst::zip_to_test << "' available in the '"
        << user_dir.u8string() << "'";

    auto [root, user] = tst::CreateInOut();
    fs::path install = root / dirs::kInstall;
    fs::create_directories(install);

    std::error_code ec;
    fs::create_directories(install, ec);
    fs::create_directories(user / dirs::kInstall, ec);
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    ON_OUT_OF_SCOPE(cma::OnStartTest());
    GetCfg().pushFolders(root, user);
    ON_OUT_OF_SCOPE(GetCfg().popFolders(););

    std::string modules_text =
        "enabled: yes\n"
        "table:\n"
        "  - name: unzip_test\n"    // valid
        "    exts: ['.test']\n"     //
        "    exec: 'nothing {}'\n"  //
        ;

    auto main_yaml = GetLoadedConfig();
    main_yaml[groups::kModules] = YAML::Load(modules_text);

    ModuleCommander mc;
    mc.readConfig(main_yaml);
    fs::copy_file(zip_file, install / tst::zip_to_test);
    ASSERT_EQ(mc.findModuleFiles(GetRootDir()), 1);

    // check installation
    auto bad_module = mc.modules_[0];
    bad_module.name_ = "zzzz";
    bad_module.dir_ = "moduleS\\zzzz";
    ASSERT_FALSE(mc.InstallModule(bad_module, root, user, InstallMode::normal));
    tst::ConstructFile(root / dirs::kFileInstallDir / "zzzz.zip", "");
    ASSERT_FALSE(mc.InstallModule(bad_module, root, user, InstallMode::normal))
        << "empty file should return false";

    ASSERT_FALSE(mc.UninstallModuleZip(fs::path(bad_module.name()),
                                       user / dirs::kUserModules))
        << "if file absent returns false";

    tst::ConstructFile(root / dirs::kFileInstallDir / "zzzz.zip",
                       "OKYYYYSSD");  // not null file should fail
    ASSERT_FALSE(mc.InstallModule(bad_module, root, user, InstallMode::normal));

    ASSERT_TRUE(
        mc.InstallModule(mc.modules_[0], root, user, InstallMode::normal));
    {
        auto target_folder = user / dirs::kUserModules / "zzzz";
        auto backup_file =
            user / dirs::kUserInstallDir / dirs::kInstalledModules / "zzzz.zip";
        ASSERT_FALSE(fs::exists(target_folder));
        ASSERT_FALSE(fs::exists(backup_file));
    }

    // check install
    auto target_folder = user / dirs::kUserModules / "unzip_test";
    auto backup_file = user / dirs::kUserInstallDir / dirs::kInstalledModules /
                       tst::zip_to_test;
    ASSERT_TRUE(fs::exists(target_folder) && fs::is_directory(target_folder));
    ASSERT_TRUE(fs::exists(backup_file) && fs::is_regular_file(backup_file));

    auto target_postinstall_folder =
        user / dirs::kUserModules / "unzip_test" / "DLLS";
    EXPECT_TRUE(fs::exists(target_postinstall_folder) &&
                fs::is_directory(target_postinstall_folder));

    // check duplicated install
    ASSERT_FALSE(
        mc.InstallModule(mc.modules_[0], root, user, InstallMode::normal));
    ASSERT_TRUE(fs::exists(target_folder) && fs::is_directory(target_folder));
    ASSERT_TRUE(fs::exists(backup_file) && fs::is_regular_file(backup_file));

    // check forced install
    ASSERT_TRUE(
        mc.InstallModule(mc.modules_[0], root, user, InstallMode::force));
    ASSERT_TRUE(fs::exists(target_folder) && fs::is_directory(target_folder));
    ASSERT_TRUE(fs::exists(backup_file) && fs::is_regular_file(backup_file));

    // check uninstall
    auto mod_backup = mc.GetModBackup(user);
    auto mod_install = mc.GetModInstall(user);

    auto installed = mc.ScanDir(mod_backup);

    ASSERT_EQ(installed.size(), 1);
    ASSERT_TRUE(mc.isBelongsToModules(installed[0]));
    ASSERT_TRUE(mc.UninstallModuleZip(installed[0], mod_install));
    installed = mc.ScanDir(mod_backup);

    ASSERT_TRUE(installed.empty());
    ASSERT_TRUE(!fs::exists(backup_file));

    // Simulate full install
    mc.installModules(root, user, InstallMode::normal);
    ASSERT_TRUE(fs::exists(target_folder) && fs::is_directory(target_folder));
    ASSERT_TRUE(fs::exists(backup_file) && fs::is_regular_file(backup_file));

    // Simulate install of the empty file(as packaged)
    tst::ConstructFile(root / dirs::kFileInstallDir / tst::zip_to_test, "");
    mc.installModules(root, user, InstallMode::normal);
    ASSERT_TRUE(!fs::exists(target_folder));
    ASSERT_TRUE(!fs::exists(backup_file));
}

}  // namespace cma::cfg::modules
