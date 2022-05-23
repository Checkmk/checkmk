// test-yaml.cpp :
// YAML and around

#include "pch.h"

#include <filesystem>

#include "cap.h"
#include "cfg.h"
#include "cfg_details.h"
#include "commander.h"
#include "common/cfg_info.h"
#include "common/mailslot_transport.h"
#include "common/wtools.h"
#include "common/yaml.h"
#include "install_api.h"
#include "providers/mrpe.h"
#include "read_file.h"
#include "service_processor.h"
#include "test_tools.h"
#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"
#include "upgrade.h"

using namespace std::chrono_literals;
namespace fs = std::filesystem;

// we want to avoid those data public
namespace cma {
void ResetCleanOnExit();
}  // namespace cma

namespace cma::commander {

static bool GetEnabledFlag(bool dflt) {
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    return cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, true);
}

static void SetEnabledFlag(bool flag) {
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    yaml_global[cma::cfg::vars::kEnabled] = flag;
}

TEST(Cma, Commander) {
    using namespace std::chrono_literals;
    //
    auto temp_cfg = tst::TempCfgFs::Create();
    ASSERT_TRUE(temp_cfg->loadFactoryConfig());
    auto yaml = cma::cfg::GetLoadedConfig();
    auto yaml_global = yaml[cma::cfg::groups::kGlobal];
    EXPECT_TRUE(yaml_global[cma::cfg::vars::kEnabled].IsScalar());
    auto enabled =
        cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, false);
    ASSERT_TRUE(enabled);
    SetEnabledFlag(false);
    enabled = cma::cfg::GetVal(yaml_global, cma::cfg::vars::kEnabled, true);
    ASSERT_FALSE(enabled);
    cma::commander::RunCommand("a", cma::commander::kReload);
    EXPECT_FALSE(enabled);
    cma::commander::RunCommand(cma::commander::kMainPeer, "aa");
    EXPECT_FALSE(enabled);

    cma::commander::RunCommand(cma::commander::kMainPeer, "aa");
    EXPECT_FALSE(enabled);

    EXPECT_NO_THROW(cma::commander::RunCommand("", ""));
    cma::commander::RunCommand(cma::commander::kMainPeer,
                               cma::commander::kReload);
    enabled = GetEnabledFlag(false);
    EXPECT_TRUE(enabled);
    SetEnabledFlag(false);

    cma::MailSlot mailbox("WinAgentTestLocal", 0);
    using namespace cma::carrier;
    auto internal_port =
        BuildPortName(kCarrierMailslotName, mailbox.GetName());  // port here
    cma::srv::ServiceProcessor processor;
    mailbox.ConstructThread(
        cma::srv::SystemMailboxCallback, 20, &processor,
        wtools::SecurityLevel::standard);  // standard is intentional
    ON_OUT_OF_SCOPE(mailbox.DismantleThread());
    cma::tools::sleep(100ms);

    cma::carrier::CoreCarrier cc;
    // "mail"
    auto ret = cc.establishCommunication(internal_port);
    EXPECT_TRUE(ret) << fmt::format("Failed port '{}'", internal_port);
    cc.sendCommand(cma::commander::kMainPeer, "a");
    cma::tools::sleep(100ms);
    enabled = GetEnabledFlag(true);
    EXPECT_FALSE(enabled);
    cc.sendCommand(cma::commander::kMainPeer, cma::commander::kReload);
    cma::tools::sleep(100ms);

    enabled = GetEnabledFlag(false);
    EXPECT_TRUE(enabled);

    cc.shutdownCommunication();
}
}  // namespace cma::commander

namespace cma::cfg {

std::string packaged_ini(kIniFromInstallMarker);

namespace details {
TEST(CmaCfg, InitEnvironment) {
    auto msi = FindMsiExec();
    auto host = FindHostName();

    ConfigInfo ci;
    EXPECT_TRUE(ci.getCwd().empty());
    EXPECT_TRUE(ci.getMsiExecPath().empty());
    EXPECT_TRUE(ci.getHostName().empty());
    ci.initEnvironment();
    EXPECT_EQ(ci.getCwd(), std::filesystem::current_path().wstring());
    EXPECT_EQ(ci.getMsiExecPath(), msi);
    EXPECT_EQ(ci.getHostName(), host);

    cma::OnStartTest();
    EXPECT_FALSE(cma::cfg::GetUserDir().empty());
}

TEST(CmaCfg, LogFileLocation) {
    namespace fs = std::filesystem;
    //
    cma::OnStartTest();
    fs::path expected = GetUserDir();
    expected /= dirs::kLog;

    {
        // default config to data/log
        fs::path dflt = details::GetDefaultLogPath();
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), expected.u8string()));
    }

    {
        // empty data to user/public
        auto &user = GetCfg().folders_.data_;
        auto old_user = user;
        ON_OUT_OF_SCOPE(GetCfg().folders_.data_ = old_user);
        user.clear();
        fs::path dflt = details::GetDefaultLogPath();
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), "c:\\Users\\public"));
    }

    {
        // empty gives us default to the data/log
        fs::path dflt = details::ConvertLocationToLogPath("");
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), expected.u8string()));
    }

    {
        // empty without user gives us default to the public/user
        auto &user = GetCfg().folders_.data_;
        auto old_user = user;
        ON_OUT_OF_SCOPE(GetCfg().folders_.data_ = old_user);
        user.clear();

        fs::path dflt = details::ConvertLocationToLogPath("");
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), "c:\\Users\\public"));
    }

    {
        // non empty gives us the dir
        fs::path dflt = details::ConvertLocationToLogPath("c:\\Windows\\Logs");
        EXPECT_TRUE(!dflt.empty());
        EXPECT_TRUE(cma::tools::IsEqual(dflt.u8string(), "c:\\Windows\\Logs"));
    }
}
}  // namespace details

TEST(CmaCfg, RemoveLegacy_Base) {
    using namespace cma::install;
    if (upgrade::FindLegacyAgent().empty()) {
        XLOG::SendStringToStdio(
            "To test Agent, you have to install Legacy Agent",
            XLOG::Colors::yellow);
        return;
    }
    // set default
    wtools::SetRegistryValue(registry::GetMsiRegistryPath(),
                             registry::kMsiRemoveLegacy,
                             registry::kMsiRemoveLegacyDefault);

    EXPECT_FALSE(rm_lwa::IsRequestedByRegistry());
    EXPECT_FALSE(rm_lwa::IsAlreadyRemoved());
    EXPECT_FALSE(rm_lwa::IsToRemove());

    // set already
    wtools::SetRegistryValue(registry::GetMsiRegistryPath(),
                             registry::kMsiRemoveLegacy,
                             registry::kMsiRemoveLegacyAlready);

    EXPECT_FALSE(rm_lwa::IsRequestedByRegistry());
    EXPECT_TRUE(rm_lwa::IsAlreadyRemoved());
    EXPECT_FALSE(rm_lwa::IsToRemove());

    // set request
    wtools::SetRegistryValue(registry::GetMsiRegistryPath(),
                             registry::kMsiRemoveLegacy,
                             registry::kMsiRemoveLegacyRequest);
    EXPECT_TRUE(rm_lwa::IsRequestedByRegistry());
    EXPECT_FALSE(rm_lwa::IsAlreadyRemoved());
    EXPECT_TRUE(rm_lwa::IsToRemove());

    // set already with high-level API
    rm_lwa::SetAlreadyRemoved();

    EXPECT_FALSE(rm_lwa::IsRequestedByRegistry());
    EXPECT_TRUE(rm_lwa::IsAlreadyRemoved());
    EXPECT_FALSE(rm_lwa::IsToRemove());

    ON_OUT_OF_SCOPE(wtools::SetRegistryValue(
        registry::GetMsiRegistryPath(), registry::kMsiRemoveLegacy,
        registry::kMsiRemoveLegacyDefault));
}

TEST(CmaCfg, RemoveLegacy_Long) {
    namespace fs = std::filesystem;
    auto temp_dir = cma::cfg::GetTempDir();
    auto path = cma::cfg::CreateWmicUninstallFile(temp_dir, "zzz");
    EXPECT_TRUE(!path.empty());
    EXPECT_TRUE(fs::exists(path));
    auto content = cma::tools::ReadFileInString(path.wstring().c_str());
    ON_OUT_OF_SCOPE(fs::remove(path););
    ASSERT_TRUE(content.has_value());
    EXPECT_EQ(content.value(), cma::cfg::CreateWmicCommand("zzz"));
    auto result = cma::cfg::UninstallProduct("zzz");
    EXPECT_TRUE(result);
}

TEST(CmaCfg, SmallFoos) {
    auto s = ConstructTimeString();
    EXPECT_TRUE(!s.empty());
}

TEST(CmaCfg, InstallProtocol) {
    auto name = ConstructInstallFileName(cma::cfg::GetRootDir());
    EXPECT_TRUE(!name.empty());
    auto str = name.string();
    EXPECT_TRUE(str.find(files::kInstallProtocol) != std::string::npos);

    name = ConstructInstallFileName("");
    EXPECT_TRUE(name.empty());
}

TEST(CmaCfg, Modules) {
    ASSERT_TRUE(!cma::cfg::GetUserModulesDir().empty());
    ASSERT_TRUE(std::wstring(cma::cfg::dirs::kUserModules) == L"modules");
    ASSERT_TRUE(std::wstring(cma::cfg::dirs::kInstalledModules) == L"modules");
    ASSERT_TRUE(envs::kMkModulesDirName == "MK_MODULESDIR");
    auto all_dir = details::AllDirTable();

    ASSERT_TRUE(std::any_of(
        std::begin(all_dir), std::end(all_dir),
        [](std::wstring_view dir) { return dir == dirs::kUserModules; }));

    auto removable_dir = details::AllDirTable();
    ASSERT_TRUE(std::any_of(
        std::begin(removable_dir), std::end(removable_dir),
        [](std::wstring_view dir) { return dir == dirs::kUserModules; }));
}

TEST(CmaCfg, ProcessPluginEnvironment) {
    //
    cma::OnStartTest();
    std::vector<std::pair<std::string, std::string>> pairs;
    ProcessPluginEnvironment(
        [&pairs](std::string_view name, std::string_view value) {
            pairs.emplace_back(std::string(name), std::string(value));
        });

    EXPECT_EQ(pairs.size(), 10) << "Count of environment variables";
    auto ret = std::none_of(pairs.begin(), pairs.end(),
                            [](std::pair<std::string, std::string> p) {
                                return p.first.empty() || p.second.empty();
                            });
    EXPECT_TRUE(ret);
    //
}

TEST(CmaCfg, InstallationTypeCheck) {
    namespace fs = std::filesystem;
    //
    auto temp_fs{tst::TempCfgFs::Create()};

    fs::path install_yml{fs::path(dirs::kFileInstallDir) /
                         files::kInstallYmlFileW};

    // without
    ASSERT_TRUE(temp_fs->createRootFile(install_yml,
                                        "# Wato\nglobal:\n  enabled: yes\n"));

    EXPECT_EQ(DetermineInstallationType(), InstallationType::wato);
    ASSERT_TRUE(temp_fs->createRootFile(
        install_yml, "# packaged\nglobal:\n  install: no\n  enabled: yes\n"));

    EXPECT_EQ(DetermineInstallationType(), InstallationType::packaged);

    // Absent:
    temp_fs->removeRootFile(install_yml);
    EXPECT_EQ(DetermineInstallationType(), InstallationType::wato);
}

namespace details {
TEST(CmaToolsDetails, FindServiceImage) {
    EXPECT_TRUE(FindServiceImagePath(L"").empty());
    auto x = FindServiceImagePath(L"check_mk_agent");
    if (x.empty()) {
        XLOG::SendStringToStdio(
            "Legacy Agent is not installed, test is not full",
            XLOG::Colors::yellow);
    } else {
        EXPECT_TRUE(std::filesystem::exists(x));
    }
}
TEST(CmaToolsDetails, ExtractPathFromServiceName) {
    auto x = ExtractPathFromServiceName(L"check_mk_agent");
    if (x.empty()) {
        XLOG::SendStringToStdio(
            "Legacy Agent is not installed, test is not full",
            XLOG::Colors::yellow);
    } else {
        EXPECT_TRUE(std::filesystem::exists(x));
        EXPECT_TRUE(cma::tools::IsEqual(x.u8string(),
                                        "c:\\Program Files (x86)\\check_mk"));
    }
}

TEST(CmaToolsDetails, FindRootByExePath) {
    using namespace std::literals;
    auto x = ExtractPathFromServiceName(L"checkmkservice");
    if (std::filesystem::exists(x)) {
        auto x_no_ext = x / "check_mk_agent";
        auto x_with_ext = x / "check_mk_agent.exe";
        auto path = L"\""s + x_with_ext.wstring() + L"\""s;
        auto upper_path = path;
        cma::tools::WideUpper(upper_path);

        auto valid_path = x.wstring();

        EXPECT_EQ(valid_path, FindRootByExePath(path));
        EXPECT_EQ(valid_path, FindRootByExePath(upper_path));
        EXPECT_EQ(valid_path, FindRootByExePath(x_no_ext.wstring()));
    } else {
        GTEST_SKIP() << "agent not installed test is not possible";
    }
}

}  // namespace details

TEST(Cma, FindAlternateDirs) {
    for (auto app_type :
         {AppType::exe, AppType::automatic, AppType::failed, AppType::srv}) {
        auto [r, d] = cma::FindAlternateDirs(app_type);
        EXPECT_EQ(r, "");
        EXPECT_EQ(d, "");
    }

    auto expected = tools::win::GetEnv(env::unit_base_dir);
    auto [r, d] = cma::FindAlternateDirs(AppType::test);
    EXPECT_TRUE(r.wstring().find(expected) != std::wstring::npos);
    EXPECT_TRUE(d.wstring().find(expected) != std::wstring::npos);
}

class CmaFixture : public ::testing::Test {
public:
    void SetUp() override {
        expected_ = tst::MakeTempFolderInTempPath(L"special_dir");
        fs::create_directories(expected_ / "test" / "root");
        fs::create_directories(expected_ / "test" / "data");
        tools::win::SetEnv(std::wstring{env::test_integration_root},
                           expected_.wstring());
    }
    void TearDown() override {
        tools::win::SetEnv(std::wstring{env::test_integration_root}, {});
        fs::remove_all(expected_);
    }
    fs::path expected_;
};
TEST_F(CmaFixture, FindAlternateDirsExeEnvVar) {
    auto [r, d] = cma::FindAlternateDirs(AppType::exe);
    EXPECT_TRUE(r.wstring().find(expected_) != std::wstring::npos);
    EXPECT_TRUE(d.wstring().find(expected_) != std::wstring::npos);
}

TEST(CmaCfg, ReloadCfg) {
    cma::OnStartTest();
    auto id = GetCfg().uniqId();
    EXPECT_TRUE(id > 0);
    cma::LoadConfigFull({});
    auto id2 = GetCfg().uniqId();
    EXPECT_TRUE(id2 > id);
}

TEST(Cma, CleanApi) {
    auto &alert = cma::g_uninstall_alert;
    ASSERT_FALSE(alert.isSet()) << "initial always false";
    alert.clear();
    ASSERT_FALSE(alert.isSet());
    alert.set();
    ASSERT_FALSE(alert.isSet())
        << "forbidden to set for non service executable";
    const auto m = GetModus();
    ON_OUT_OF_SCOPE(cma::details::SetModus(m));
    cma::details::SetModus(cma::Modus::service);
    alert.set();
    EXPECT_TRUE(alert.isSet());
    cma::details::SetModus(m);
    alert.clear();
    EXPECT_FALSE(alert.isSet());
}

TEST(Cma, PushPop) {
    cma::OnStartTest();
    namespace fs = std::filesystem;
    tst::SafeCleanTempDir();
    auto [r, u] = tst::CreateInOut();
    auto root = r.wstring();
    auto user = u.wstring();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir(););
    std::error_code ec;

    auto old_root = GetRootDir();
    auto old_user = GetUserDir();

    ASSERT_TRUE(GetCfg().pushFolders(root, user));
    EXPECT_EQ(root, GetRootDir());
    EXPECT_EQ(user, GetUserDir());

    GetCfg().popFolders();
    EXPECT_EQ(old_root, GetRootDir());
    EXPECT_EQ(old_user, GetUserDir());

    for (size_t k = 0; k < details::kMaxFoldersStackSize; k++) {
        EXPECT_TRUE(GetCfg().pushFolders(root, user));
        EXPECT_EQ(root, GetRootDir());
        EXPECT_EQ(user, GetUserDir());
    }
    EXPECT_FALSE(GetCfg().pushFolders(root, user));

    for (size_t k = 0; k < details::kMaxFoldersStackSize; k++) {
        EXPECT_TRUE(GetCfg().popFolders());
    }
    EXPECT_FALSE(GetCfg().popFolders());
    EXPECT_EQ(old_root, GetRootDir());
    EXPECT_EQ(old_user, GetUserDir());
}

}  // namespace cma::cfg

namespace cma::cfg {
TEST(CmaCfg, ConfigManagement) {
    auto node = CreateNode("test");
    ASSERT_TRUE(node);
    node->setConfiguredLogFileDir(L"test");
    auto node2 = GetNode("test");
    EXPECT_EQ(node2->getConfiguredLogFileDir(), L"test");
    ASSERT_TRUE(node2);
    RemoveNode("test");
    auto node3 = GetNode("test");
    ASSERT_FALSE(node3);
}

}  // namespace cma::cfg

namespace cma::srv {
TEST(CmaCfg, RestartBinaries) {
    cma::srv::ServiceProcessor sp;
    uint64_t id = cma::cfg::GetCfg().uniqId();
    auto old_id = id;
    EXPECT_FALSE(sp.restartBinariesIfCfgChanged(id));
    EXPECT_EQ(old_id, id);
    ReloadConfig();
    EXPECT_TRUE(sp.restartBinariesIfCfgChanged(id));
    EXPECT_NE(old_id, id);
}

}  // namespace cma::srv

namespace cma::cfg {
class CmaCfg_F : public ::testing::Test {
protected:
    void SetUp() override {
        temp_fs_ = tst::TempCfgFs::Create();
        ASSERT_TRUE(temp_fs_->loadFactoryConfig());
        cap_base_ = tst::MakePathToCapTestFiles() / "plugins.test.cap";

        root_ = temp_fs_->root().wstring();
        user_ = temp_fs_->data().wstring();
    }

    void TearDown() override {}

    auto prepareAll() {
        fs::path pd = GetUserDir();
        details::CreateTree(pd);
        auto table = details::AllDirTable();
        auto table_removed = details::RemovableDirTable();
        for (auto &n : table) {
            tst::CreateTextFile(pd / n / "1.tmp", wtools::ToUtf8(n));
        }

        user_folders_count_ = table.size() - table_removed.size();

        return std::make_tuple(pd, table, table_removed);
    }

    std::wstring root_;
    std::wstring user_;
    std::filesystem::path cap_base_;
    size_t user_folders_count_ = 0;

    tst::TempCfgFs::ptr temp_fs_;
};

TEST_F(CmaCfg_F, CreateTree) {
    ASSERT_TRUE(GetRootDir() == root_);
    ASSERT_TRUE(GetUserDir() == user_);
    fs::path pd = GetUserDir();
    details::CreateTree(pd);
    auto table = details::AllDirTable();
    for (auto &n : table)
        ASSERT_TRUE(fs::is_directory(pd / n))
            << "Doesn't exist: " << n.data() << "\n";
}

TEST_F(CmaCfg_F, CleanInstallOnInvalidFolder) {
    // prepare damaged folder
    fs::path user_dir = cma::cfg::GetUserDir();
    fs::remove_all(user_dir / dirs::kBakery);

    for (auto m : {details::CleanMode::none, details::CleanMode::smart,
                   details::CleanMode::all})
        ASSERT_FALSE(details::CleanDataFolder(m))
            << "Tmp Folder cannot be processed";
}

TEST_F(CmaCfg_F, CleanDataFolderNoneAllSmartEmpty) {
    auto [pd, table, table_removed] = prepareAll();

    ASSERT_TRUE(details::CleanDataFolder(details::CleanMode::none));

    for (auto &n : table) {
        EXPECT_TRUE(fs::exists(pd / n / "1.tmp"))
            << "directory doesn't exist: " << n.data();
    }

    // check that all removes all folders
    ASSERT_TRUE(details::CleanDataFolder(details::CleanMode::all));

    for (auto &n : table) {
        EXPECT_TRUE(!fs::exists(pd / n));
    }

    // check that smart removes also all empty folders
    details::CreateTree(pd);
    for (auto &n : table_removed) {
        EXPECT_TRUE(fs::exists(pd / n));
    }
    details::CleanDataFolder(details::CleanMode::smart);

    for (auto &n : table) {
        if (n == dirs::kLog) {
            continue;
        }
        EXPECT_EQ(fs::exists(pd / n), !details::g_remove_dirs_on_clean)
            << (pd / n).string();
    }
}

TEST_F(CmaCfg_F, CleanDataFolderSmart) {
    auto [pd, table, table_removed] = prepareAll();

    // test additional preparation
    ASSERT_TRUE(fs::exists(cap_base_));
    auto [tgt, ignored] = cap::GetInstallPair(files::kCapFile);
    ASSERT_TRUE(fs::copy_file(cap_base_, tgt));

    std::vector<std::wstring> files;
    cap::Process(tgt.u8string(), cap::ProcMode::install, files);
    ASSERT_TRUE(files.size() > 0);
    for (auto &f : files) {
        EXPECT_TRUE(fs::exists(f));
    }

    auto [target_yml_example, ignore_it_again] = cap::GetExampleYmlNames();
    tst::CreateTextFile(target_yml_example, "aaa");
    tst::CreateTextFile(pd / files::kUserYmlFile, "aaa");

    ASSERT_TRUE(details::CleanDataFolder(details::CleanMode::smart));
    for (auto &f : files) {
        EXPECT_TRUE(!fs::exists(f));
    }
    EXPECT_TRUE(!fs::exists(target_yml_example));
    EXPECT_TRUE(!fs::exists(pd / files::kUserYmlFile));

    for (auto &n : table_removed) {
        EXPECT_EQ(fs::exists(pd / n), !details::g_remove_dirs_on_clean)
            << "directory state is invalid : " << n.data();
    }

    // restore removed folders
    details::CreateTree(pd);

    // different user and example yml
    tst::CreateTextFile(target_yml_example, "aaa");
    tst::CreateTextFile(pd / files::kUserYmlFile, "aaabb");

    ASSERT_TRUE(details::CleanDataFolder(details::CleanMode::smart));

    EXPECT_TRUE(!fs::exists(target_yml_example));
    EXPECT_TRUE(fs::exists(pd / files::kUserYmlFile))
        << "this file must be left on disk";

    int exists_count = 0;
    for (auto &n : table) {
        if (fs::exists(pd / n / "1.tmp")) ++exists_count;
    }

    EXPECT_EQ(exists_count == user_folders_count_,
              details::g_remove_dirs_on_clean)
        << "you delete wrong count of folders";
}

namespace {
class JobToCheckEnvironment {
public:
    JobToCheckEnvironment(const std::string &case_name)
        : dirs{case_name}
        , cmd_file_{dirs.in() / "printer.cmd"}
        , results_file_{dirs.out() / "results.txt"} {}

    std::vector<std::string> getEnvironment() {
        createScript();
        return runScript();
    }

private:
    void createScript() {
        auto bat_file = fmt::format(
            "@echo start>{0}\n"
            "@if defined MK_STATEDIR echo %MK_STATEDIR%>>{0}\n"
            "@if defined MK_CONFDIR echo %MK_CONFDIR%>>{0}\n"
            "@if defined MK_LOCALDIR echo %MK_LOCALDIR%>>{0}\n"
            "@if defined MK_TEMPDIR echo %MK_TEMPDIR%>>{0}\n"
            "@if defined MK_SPOOLDIR echo %MK_SPOOLDIR%>>{0}\n"
            "@if defined MK_PLUGINSDIR echo %MK_PLUGINSDIR%>>{0}\n"
            "@if defined MK_LOGDIR echo %MK_LOGDIR%>>{0}\n"
            "@if defined REMOTE_HOST echo %REMOTE_HOST%>>{0}\n"
            "@if defined REMOTE echo %REMOTE%>>{0}\n"
            "@if defined MK_INSTALLDIR echo %MK_INSTALLDIR%>>{0}\n"
            "@if defined MK_MODULESDIR echo %MK_MODULESDIR%>>{0}\n"
            "@if defined MK_MSI_PATH echo %MK_MSI_PATH%>>{0}\n",
            results_file_);

        std::ofstream ofs(cmd_file_);

        ofs << bat_file;
    }

    std::vector<std::string> runScript() {
        auto [pid, job, process] =
            tools::RunStdCommandAsJob(cmd_file_.wstring());
        tst::WaitForSuccessSilent(1000ms, [process]() {
            DWORD code = 0;
            auto success = ::GetExitCodeProcess(process, &code);
            return success == TRUE && code != STILL_ACTIVE;
        });

        ::TerminateJobObject(job, 21);
        ::CloseHandle(job);
        ::CloseHandle(process);
        return tst::ReadFileAsTable(results_file_);
    }

    tst::TempDirPair dirs;
    fs::path cmd_file_;
    fs::path results_file_;
};
}  // namespace

TEST(CmaCfg, SetupPluginEnvironmentIntegration) {
    JobToCheckEnvironment job(test_info_->name());
    cfg::SetupPluginEnvironment();
    auto table = job.getEnvironment();

    // check for uniqueness
    std::set<std::string> all;
    for (auto const &raw : table) {
        all.insert(raw);
    }
    EXPECT_EQ(all.size(), 11);
}

}  // namespace cma::cfg
