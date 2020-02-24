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
bool Compare(const T &t, const T &v) {
    static_assert(cma::tools::is_iterable<T>::value);
    if (t.size() != v.size()) return false;

    return std::equal(t.begin(), t.end(), v.begin());
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

    m.exec_ = L"a";
    m.exts_.emplace_back("v");
    m.name_ = "z";
    EXPECT_EQ(m.exec(), L"a");
    EXPECT_EQ(m.name(), "z");
    EXPECT_TRUE(Compare(m.exts(), {"v"}));
    EXPECT_TRUE(m.valid());

    // reset test
    m.reset();
    EXPECT_FALSE(m.valid());
    EXPECT_TRUE(m.exec().empty());
    EXPECT_TRUE(m.exts().empty());
    EXPECT_TRUE(m.name().empty());
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
        {"the-1.0", "[.e1, .e2]", "x", "dir: modules\\{}"},  // full
        {"the-1.0", "[.e1]", "x", "dir: "},                  // empty dir
        {"the-1.0", "[.e1]", "x", ""},                       // empty dir
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

TEST(ModuleCommanderTest, ReadConfig) {
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

TEST(ModuleCommanderTest, FindModules) {
    using namespace std::literals;
    namespace fs = std::filesystem;
    cma::OnStartTest();
    tst::SafeCleanTempDir();
    fs::path root = cma::cfg::GetTempDir();
    fs::path install = tst::CreateDirInTemp(dirs::kInstall);
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());

    std::string base =
        "modules:\n"
        "  enabled: yes\n"
        "  table:\n"
        "    - name: real_module_module\n"   // valid
        "      exts: ['.test']\n"            //
        "      exec: 'nothing {}'\n"         //
        "    - name: real_module_module2\n"  // valid
        "      exts: ['.test2']\n"           //
        "      exec: 'nothing2 {}'\n"        //
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

TEST(ModuleCommanderTest, Internal) {
    using namespace std::literals;
    namespace fs = std::filesystem;
    cma::OnStartTest();
    fs::path user_dir = cma::cfg::GetUserDir();
    tst::SafeCleanTempDir();
    fs::path user = cma::cfg::GetTempDir();
    fs::path modules = ModuleCommander::GetModInstall(user);
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());

    ModuleCommander mc;
    auto dir = user / dirs::kUserModules / "tst";
    EXPECT_FALSE(mc.createFileForTargetDir("c:\\windows", modules));
    EXPECT_FALSE(mc.createFileForTargetDir(modules / "tst", "c:\\windows"));
    EXPECT_TRUE(mc.createFileForTargetDir(modules / "tst", modules));

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

    EXPECT_TRUE(mc.removeContentByTargetDir({}, modules / "tst"));
    EXPECT_FALSE(mc.removeContentByTargetDir({L"doc"}, modules / "t"));

    EXPECT_FALSE(mc.removeContentByTargetDir({L"doc", L"test.txt"}, {}));

    EXPECT_TRUE(
        mc.removeContentByTargetDir({L"doc", L"test.txt"}, modules / "tst"));
    EXPECT_FALSE(fs::exists(modules / "doc"));
    EXPECT_FALSE(fs::exists(modules / "test.txt"));
    EXPECT_TRUE(fs::exists(modules / "test_left.txt"));
}

TEST(ModuleCommanderTest, InstallModules) {
    using namespace std::literals;
    namespace fs = std::filesystem;
    cma::OnStartTest();
    tst::SafeCleanTempDir();
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
    ASSERT_TRUE(mc.installModule(mc.modules_[0], root,
                                 user / dirs::kUserInstallDir,
                                 InstallMode::force));
}

}  // namespace cma::cfg::modules
