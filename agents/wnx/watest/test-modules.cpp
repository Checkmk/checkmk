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

using namespace std::literals;
namespace fs = std::filesystem;

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
bool Compare(const T &t, const T &v) {
    static_assert(cma::tools::is_iterable<T>::value);
    if (t.size() != v.size()) return false;

    return std::equal(t.begin(), t.end(), v.begin());
}

TEST(ModuleCommander, CheckSystemAuto) {
    namespace fs = std::filesystem;

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
        EXPECT_TRUE(mc.isModuleScript("z.checkmk.py"));

        node["modules"]["python"] = "auto";
        mc.readConfig(node);
        ASSERT_TRUE(mc.getExtensions().size() == 2);
        EXPECT_TRUE(mc.isModuleScript("z.py"));
        EXPECT_TRUE(mc.isModuleScript("z.checkmk.py"));
    }

    {
        ModuleCommander mc;
        auto node = YAML::Load(base_1);
        node["modules"]["python"] = "system";
        mc.readConfig(node);
        ASSERT_TRUE(mc.getExtensions().size() == 1);
        EXPECT_FALSE(mc.isModuleScript("z.py"));
        EXPECT_TRUE(mc.isModuleScript("z.checkmk.py"));
    }
}

namespace {
void LoadContentWithoutQuickReinstall() {
    ASSERT_TRUE(
        cfg::GetCfg().loadDirect("global:\n"
                                 "  enabled: yes\n"
                                 "modules:\n"
                                 "  enabled: yes\n"
                                 "  quick_reinstall: no\n"sv));
}

}  // namespace

TEST(ModulesTest, QuickInstallEnabled) {
    // NOTE: normally we do not test constants, but this is business decision
    // which may differ for different branches
    ASSERT_TRUE(g_quick_module_reinstall_allowed);

    {
        auto temp_fs{tst::TempCfgFs::CreateNoIo()};
        ASSERT_TRUE(temp_fs->loadFactoryConfig());
        LoadContentWithoutQuickReinstall();
        EXPECT_FALSE(ModuleCommander::IsQuickReinstallAllowed());
    }
    {
        auto temp_fs{tst::TempCfgFs::CreateNoIo()};
        ASSERT_TRUE(temp_fs->loadFactoryConfig());
        EXPECT_FALSE(ModuleCommander::IsQuickReinstallAllowed());
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
    EXPECT_TRUE(m.package_.empty());

    m.exec_ = L"a";
    m.exts_.emplace_back(".v");
    m.name_ = "z";
    EXPECT_EQ(m.exec(), L"a");
    EXPECT_EQ(m.name(), "z");
    EXPECT_TRUE(Compare(m.exts(), {".v"}));
    EXPECT_TRUE(m.valid());

    m.bin_ = "z";
    EXPECT_EQ(m.bin(), "z");

    m.package_ = "z";
    EXPECT_EQ(m.package(), "z");

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
    EXPECT_TRUE(m.package().empty());
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
        "    - name: the_module\n"     // valid
        "      exts: ['.test']\n"      //
        "      exec: 'nothing {}'\n"   //
        "    - name: the_module2\n"    // valid
        "      exts: ['.test2']\n"     //
        "      exec: 'nothing2 {}'\n"  //
        "      dir:  'plugins'\n";

    ModuleCommander mc;
    auto node = YAML::Load(base);
    mc.readConfig(node);
    ASSERT_TRUE(mc.modules_.size() == 2);
    EXPECT_EQ(mc.modules_[0].name(), "the_module");
    EXPECT_EQ(mc.modules_[1].name(), "the_module2");
    EXPECT_EQ(mc.modules_[0].exec(), L"nothing {}");
    EXPECT_EQ(mc.modules_[1].exec(), L"nothing2 {}");
    EXPECT_EQ(mc.modules_[0].dir(), "modules\\the_module");
    EXPECT_EQ(mc.modules_[1].dir(), "plugins");
}

class ModuleCommanderTest : public ::testing::Test {
protected:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        fs::create_directories(temp_fs_->root() / dirs::kInstall);
        fs::create_directories(temp_fs_->data() / dirs::kUserInstallDir);
    }

    void TearDown() override {}

    tst::TempCfgFs::ptr temp_fs_;

    std::pair<fs::path, fs::path> CreateModulesAndBackup() {
        fs::path user = temp_fs_->data();
        auto modules_dir = user / dirs::kUserModules;
        auto backup_dir =
            user / dirs::kUserInstallDir / dirs::kInstalledModules;
        fs::create_directories(modules_dir);
        fs::create_directories(backup_dir);
        return {modules_dir, backup_dir};
    }

    ::testing::AssertionResult IsPresented(const fs::path &file,
                                           const fs::path &dir) {
        if (!fs::exists(file)) {
            return ::testing::AssertionFailure()
                   << file.u8string() << " is absent";
        }

        if (!fs::exists(dir)) {
            return ::testing::AssertionFailure()
                   << dir.u8string() << " is absent";
        }

        if (!fs::is_regular_file(file)) {
            return ::testing::AssertionFailure()
                   << file.u8string() << " is not a file";
        }

        if (!fs::is_directory(dir)) {
            return ::testing::AssertionFailure()
                   << dir.u8string() << " is not a dir";
        }

        return ::testing::AssertionSuccess();
    }

    ::testing::AssertionResult IsAbsent(const fs::path &file,
                                        const fs::path &dir) {
        if (fs::exists(file)) {
            return ::testing::AssertionFailure()
                   << file.u8string() << " should be absent";
        }

        if (fs::exists(dir)) {
            return ::testing::AssertionFailure()
                   << dir.u8string() << " should be absent";
        }

        return ::testing::AssertionSuccess();
    }

    std::pair<fs::path, fs::path> makeExpectedPair(const fs::path &zip_file) {
        auto name{zip_file.filename()};
        auto target_folder = temp_fs_->data() / dirs::kUserModules / name;
        target_folder.replace_extension();
        auto backup_file = temp_fs_->data() / dirs::kUserInstallDir /
                           dirs::kInstalledModules / name;

        return {backup_file, target_folder};
    }
};

TEST_F(ModuleCommanderTest, PrepareToWork) {
    auto [modules_dir, backup_dir] = CreateModulesAndBackup();

    Module m;
    std::string test_1 =
        "name: zz\n"      // valid
        "exts: ['.t']\n"  //
        "exec: 'zz.exe {}'\n";
    ASSERT_TRUE(m.loadFrom(YAML::Load(test_1)));
    ASSERT_TRUE(m.name() == "zz" && m.exec() == L"zz.exe {}");
    EXPECT_FALSE(m.prepareToWork(backup_dir, modules_dir));
    tst::CreateTextFile(backup_dir / (m.name() + kExtension.data()), "cab");
    EXPECT_FALSE(m.prepareToWork(backup_dir, modules_dir));
    EXPECT_EQ(m.package(), backup_dir / "zz.cab");
    EXPECT_TRUE(m.buildCommandLine("x.t").empty());

    fs::create_directories(modules_dir / m.name());
    tst::CreateTextFile(modules_dir / m.name() / "zz.exe", "exe");
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
    auto [modules_dir, backup_dir] = CreateModulesAndBackup();

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
    for (auto &m : mc.modules_) {
        ASSERT_TRUE(m.bin().empty());
        ASSERT_TRUE(m.package().empty());
    }

    tst::CreateTextFile(
        backup_dir / (mc.modules_[0].name() + kExtension.data()), "zip");
    mc.prepareToWork();
    {
        ASSERT_TRUE(mc.modules_[0].bin().empty());
        ASSERT_FALSE(mc.modules_[0].package().empty());
        ASSERT_TRUE(mc.modules_[1].bin().empty());
        ASSERT_TRUE(mc.modules_[1].package().empty());
    }

    fs::create_directories(modules_dir / mc.modules_[0].name());
    tst::CreateTextFile(modules_dir / mc.modules_[0].name() / "zz.exe", "exe");
    mc.prepareToWork();
    {
        ASSERT_FALSE(mc.modules_[0].bin().empty());
        ASSERT_FALSE(mc.modules_[0].package().empty());
        ASSERT_TRUE(mc.modules_[1].bin().empty());
        ASSERT_TRUE(mc.modules_[1].package().empty());
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
    fs::path user = temp_fs_->data();

    auto backup_dir = user / dirs::kUserInstallDir / dirs::kInstalledModules;
    ASSERT_FALSE(fs::exists(backup_dir));
    ModuleCommander::CreateBackupFolder(user);
    ASSERT_TRUE(fs::exists(backup_dir));

    auto mod_file = user / "to_backup";
    tst::CreateTextFile(mod_file, "11");

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
    tst::CreateTextFile(dummy_file, "aaaaa");
    ASSERT_TRUE(fs::exists(dummy_file));
    ModuleCommander::PrepareCleanTargetDir(mod_dir);
    ASSERT_TRUE(fs::exists(mod_dir));
    ASSERT_FALSE(fs::exists(dummy_file));
}

TEST_F(ModuleCommanderTest, FindModules) {
    fs::path root = temp_fs_->root();
    fs::path install = root / dirs::kInstall;

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
    tst::CreateTextFile(install / "not_module", "z");
    ASSERT_EQ(mc.findModuleFiles(root), 0);
    tst::CreateTextFile(install / ("null_module_module"s + kExtension.data()),
                        "");
    ASSERT_EQ(mc.findModuleFiles(root), 0);

    EXPECT_EQ(mc.getExtensions(),
              std::vector<std::string>({".test"s, ".test2"s, "test3.tt"s}));

    tst::CreateTextFile(install / ("real_module_module"s + kExtension.data()),
                        "zip");
    ASSERT_EQ(mc.findModuleFiles(root), 1);

    tst::CreateTextFile(install / ("real_module_module2"s + kExtension.data()),
                        "zip");
    ASSERT_EQ(mc.findModuleFiles(root), 2);

    // check that name are correctly found in modules list
    EXPECT_FALSE(mc.isBelongsToModules("c:\\windows\\real_module_module"));
    EXPECT_FALSE(mc.isBelongsToModules("c:\\windows\\real_module_module.zi"));
    EXPECT_TRUE(mc.isBelongsToModules("c:\\windows\\real_module_module.cab"));
    EXPECT_TRUE(mc.isBelongsToModules("c:\\windows\\real_module_module2.cab"));

    EXPECT_FALSE(mc.isBelongsToModules(""));
}

TEST_F(ModuleCommanderTest, InstallModulesIntegration) {
    auto zip_file = tst::MakePathToUnitTestFiles() / tst::install_cab_to_test;
    ASSERT_TRUE(fs::exists(zip_file))
        << "Please make '" << tst::install_cab_to_test << "' available";

    auto user = temp_fs_->data();
    auto root = temp_fs_->root();
    auto install = root / dirs::kInstall;

    std::string modules_text =
        "modules:\n"
        "  enabled: yes\n"
        "  table:\n"
        "    - name: install_test\n"  // valid
        "      exts: ['.test']\n"     //
        "      exec: 'nothing {}'\n"  //
        ;

    ModuleCommander mc;
    auto cfg = YAML::Load(modules_text);
    mc.readConfig(cfg);
    fs::copy_file(zip_file, install / tst::install_cab_to_test);
    ASSERT_EQ(mc.findModuleFiles(GetRootDir()), 1);

    // BAD MODULE installation
    auto bad_module = mc.modules_[0];
    bad_module.name_ = "zzzz";
    EXPECT_FALSE(mc.InstallModule(bad_module, root, user, InstallMode::normal));
    tst::CreateTextFile(root / dirs::kFileInstallDir / "zzzz.zip", "");
    EXPECT_FALSE(mc.InstallModule(bad_module, root, user, InstallMode::normal))
        << "empty file should return false";

    EXPECT_FALSE(mc.UninstallModuleZip(fs::path(bad_module.name()),
                                       user / dirs::kUserModules))
        << "if file absent returns false";

    tst::CreateTextFile(root / dirs::kFileInstallDir / "zzzz.zip",
                        "OKYYYYSSD");  // not null file should fail
    (mc.InstallModule(bad_module, root, user, InstallMode::normal));

    // Clean install store
    auto move_dir = ModuleCommander::GetMoveLocation(tst::install_cab_to_test);
    std::error_code ec;
    fs::remove_all(move_dir, ec);

    // NORMAL install
    EXPECT_TRUE(
        mc.InstallModule(mc.modules_[0], root, user, InstallMode::normal));
    auto [zzzz_backup_file, zzzz_target_folder] = makeExpectedPair("zzzz.zip");
    EXPECT_TRUE(IsAbsent(zzzz_backup_file, zzzz_target_folder));

    auto [backup_file, target_folder] =
        makeExpectedPair(tst::install_cab_to_test);
    EXPECT_TRUE(IsPresented(backup_file, target_folder));

    auto target_postinstall_folder =
        user / dirs::kUserModules / "install_test" / "DLLS";
    EXPECT_TRUE(fs::is_directory(target_postinstall_folder))
        << fmt::format("'{}' is bad or not found", target_postinstall_folder);

    // check duplicated install
    EXPECT_FALSE(
        mc.InstallModule(mc.modules_[0], root, user, InstallMode::normal));
    EXPECT_TRUE(IsPresented(backup_file, target_folder));
    // Check that files removed from the uninstall store
    EXPECT_TRUE(IsAbsent(move_dir / backup_file.filename(),
                         move_dir / mc.modules_[0].name()));

    // forced install
    EXPECT_TRUE(
        mc.InstallModule(mc.modules_[0], root, user, InstallMode::force));
    EXPECT_TRUE(IsPresented(backup_file, target_folder));

    // uninstall store must not be empty(removed from the previous installation)
    if (ModuleCommander::IsQuickReinstallAllowed()) {
        EXPECT_TRUE(IsPresented(move_dir / backup_file.filename(),
                                move_dir / mc.modules_[0].name()));

        // Poisoning: create some files/folders simulation old installation
        auto sim_dir = move_dir / mc.modules_[0].name() / "simulation";
        auto sim_file = sim_dir / "simulation.dat";
        fs::create_directories(sim_dir);
        tst::CreateBinaryFile(sim_file, "a");
        EXPECT_TRUE(fs::exists(sim_file));

        // check uninstall
        auto mod_backup = ModuleCommander::GetModBackup(user);
        auto mod_install = ModuleCommander::GetModInstall(user);

        auto installed = ModuleCommander::ScanDir(mod_backup);

        ASSERT_EQ(installed.size(), 1);
        EXPECT_TRUE(mc.isBelongsToModules(installed[0]));
        EXPECT_TRUE(mc.UninstallModuleZip(installed[0], mod_install));
        installed = ModuleCommander::ScanDir(mod_backup);

        EXPECT_TRUE(installed.empty());
        EXPECT_TRUE(!fs::exists(backup_file));

        // check that files/folders from simulated old installation removed
        EXPECT_TRUE(IsAbsent(sim_file, sim_dir));
    }

    // Simulate full install
    mc.installModules(root, user, InstallMode::normal);
    EXPECT_TRUE(IsPresented(backup_file, target_folder));

    // Simulate install of the empty file(as packaged)
    tst::CreateTextFile(root / dirs::kFileInstallDir / tst::install_cab_to_test,
                        "");
    mc.installModules(root, user, InstallMode::normal);
    EXPECT_TRUE(IsAbsent(backup_file, target_folder));

    if (ModuleCommander::IsQuickReinstallAllowed()) {
        // check uninstall store
        EXPECT_TRUE(IsPresented(move_dir / backup_file.filename(),
                                move_dir / mc.modules_[0].name()));

        // Simulate full install to check quick install
        fs::copy_file(zip_file, install / tst::install_cab_to_test,
                      fs::copy_options::overwrite_existing);
        mc.installModules(root, user, InstallMode::normal);
        EXPECT_TRUE(IsPresented(backup_file, target_folder));

        // Check that files removed from the quick uninstall
        EXPECT_TRUE(IsAbsent(move_dir / backup_file.filename(),
                             move_dir / mc.modules_[0].name()));

        // Move modules to store, this is part of deinstall process
        mc.moveModulesToStore(user);
        EXPECT_TRUE(IsAbsent(backup_file, target_folder));

        // Check that files removed from the quick uninstall
        EXPECT_TRUE(IsPresented(move_dir / backup_file.filename(),
                                move_dir / mc.modules_[0].name()));
    }
}

}  // namespace cma::cfg::modules
