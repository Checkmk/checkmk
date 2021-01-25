// test-service.cpp

//
#include "pch.h"

#include <filesystem>
#include <fstream>

#include "common/wtools.h"
#include "install_api.h"
#include "service_processor.h"
#include "test_tools.h"

namespace fs = std::filesystem;

namespace cma::install {

TEST(InstallAuto, FileControlIntegration) {
    tst::TempDirPair dirs{test_info_->name()};
    auto in = dirs.in();
    auto out = dirs.out();
    // artificial file creation
    const auto name = L"test.dat";
    auto path = in / name;

    // api functions have to fail
    EXPECT_TRUE(RmFile(path));
    EXPECT_FALSE(MvFile(path, out / name));
    EXPECT_NO_THROW(BackupFile(path, out));
    EXPECT_FALSE(NeedInstall(path, out));

    tst::CreateTextFile(path, "-----\n");

    // check for presence
    std::error_code ec;
    auto ret = fs::exists(path, ec);
    ASSERT_TRUE(ret);

    {
        std::ofstream ofs(path);
        EXPECT_FALSE(RmFile(path)) << "should fail";
    }

    EXPECT_TRUE(NeedInstall(path, out));

    EXPECT_TRUE(RmFile(path));
    EXPECT_FALSE(MvFile(path, out / name)) << "file should be removed";
    tst::CreateTextFile(path, "-----\n");
    EXPECT_TRUE(MvFile(path, out / name)) << "move has to success";

    EXPECT_NO_THROW(BackupFile(path, out));
    BackupFile(out / name, in);  // opposite direction, just check that works
    EXPECT_TRUE(fs::exists(path, ec));

    EXPECT_FALSE(NeedInstall(path, out));
    tst::CreateTextFile(path, "-----\n");
    EXPECT_TRUE(NeedInstall(path, out));
    BackupFile(path, out);
    EXPECT_FALSE(NeedInstall(path, out));
}

TEST(InstallAuto, GlobalSettings) {
    EXPECT_EQ(GetInstallMode(), InstallMode::normal);
}

class InstallAutoPrepareFixture : public ::testing::Test {
public:
    static void SetUpTestSuite() {
        script_log_file_ = cfg::GetLogDir();
        script_log_file_ /= "execute_script.log";
        temp_script_dir_ =
            fmt::format(L"\\cmk_update_agent_{}\\", ::GetCurrentProcessId());

        eu_ = std::make_unique<ExecuteUpdate>();
        eu_->prepare(L"msi exec", L"x x x", false);
        msi_log_file_ = eu_->getLogFileName();
        temp_script_file_ = eu_->getTempScriptFile();
        expected_cmd_line_ =
            fmt::format(LR"("{}" "msi exec" "/i x x x /qn /L*V {}" "{}")",
                        temp_script_file_.wstring(), msi_log_file_,
                        script_log_file_.wstring());
    }

    // ***************************************************
    // NOTE: inline makes our life a bit easier.
    // Attention: We must use unique_ptr, because constructing during EXE init
    // will fail.
    // ***************************************************
    static inline std::unique_ptr<ExecuteUpdate> eu_;
    static inline std::filesystem::path script_log_file_;
    static inline std::wstring temp_script_dir_;
    static inline std::wstring msi_log_file_;
    static inline std::filesystem::path temp_script_file_;
    static inline std::wstring expected_cmd_line_;
};

TEST_F(InstallAutoPrepareFixture, TempScriptFile) {
    // temp script should be located in temp script dir
    EXPECT_TRUE(temp_script_file_.wstring().find(temp_script_dir_) !=
                std::string::npos);

    // temp script name is predefined
    EXPECT_EQ(temp_script_file_.filename(),
              fs::path(cfg::files::kExecuteUpdateFile));
}

TEST_F(InstallAutoPrepareFixture, MsiLogPath) {
    // msi log file name is predefined
    EXPECT_EQ(fs::path(msi_log_file_).filename(), fs::path(kMsiLogFileName));
}

TEST_F(InstallAutoPrepareFixture, GetCommand) {
    EXPECT_EQ(eu_->getCommand(), expected_cmd_line_);
}

class InstallAutoSimulationFixture : public testing::Test {
protected:
    static void SetUpTestSuite() {
        fs_ = std::make_unique<tst::TempCfgFs>();
        eu_ = std::make_unique<ExecuteUpdate>();
        ASSERT_TRUE(fs_->loadConfig(tst::GetFabricYml()));
        eu_->prepare(L"msi", L"x x x", true);

        tst::CreateWorkFile(eu_->getLogFileName(), "This is log");

        fs::create_directories(fs_->root() / cfg::dirs::kAgentUtils);
        tst::CreateWorkFile(fs_->root() / cfg::dirs::kAgentUtils /
                                cfg::files::kExecuteUpdateFile,
                            "This is  script");
    }

    static void TearDownTestSuite() {}

    // ***************************************************
    // NOTE: inline makes our life a bit easier.
    // Attention: We must use unique_ptr, because constructing during EXE init
    // will fail.
    // ***************************************************
    static inline std::unique_ptr<tst::TempCfgFs> fs_;
    static inline std::unique_ptr<ExecuteUpdate> eu_;
};

TEST_F(InstallAutoSimulationFixture, BackupLogIntegration) {
    fs::path log_bak_file{eu_->getLogFileName()};
    log_bak_file.replace_extension(".log.bak");

    // perform backup of the log action
    eu_->backupLog();

    // expected copy of log
    EXPECT_TRUE(fs::exists(log_bak_file));
}

TEST_F(InstallAutoSimulationFixture, CopyScriptToTempIntegration) {
    eu_->copyScriptToTemp();
    EXPECT_TRUE(fs::exists(eu_->getTempScriptFile()));
}

extern bool g_use_script_to_install;
TEST(InstallAuto, PrepareExecutionLegacy) {
    g_use_script_to_install = false;
    ON_OUT_OF_SCOPE(g_use_script_to_install = true);

    EXPECT_EQ(GetInstallMode(), InstallMode::normal);

    ExecuteUpdate eu;
    eu.prepare(L"msi-exec", L"xx.msi", false);
    EXPECT_EQ(eu.getCommand(), fmt::format(LR"(msi-exec /i xx.msi /qn /L*V {})",
                                           eu.getLogFileName()));

    EXPECT_EQ(fs::path(eu.getLogFileName()).filename(),
              fs::path(kMsiLogFileName));
}

TEST(InstallAuto, PrepareExecutionFallback) {
    ASSERT_TRUE(g_use_script_to_install);

    EXPECT_EQ(GetInstallMode(), InstallMode::normal);

    ExecuteUpdate eu;
    eu.prepare(L"msi-exec", L"xx.msi", true);
    auto msi_log_file = eu.getLogFileName();
    auto command = eu.getCommand();
    EXPECT_EQ(command,
              fmt::format(LR"(msi-exec /i xx.msi /qn /L*V {})", msi_log_file));

    EXPECT_EQ(fs::path(msi_log_file).filename().u8string(), kMsiLogFileName);
}

TEST(InstallAuto, CheckForUpdateFileIntegration) {
    namespace fs = std::filesystem;
    auto msi = cma::cfg::GetMsiExecPath();
    ASSERT_TRUE(!msi.empty());

    tst::TempCfgFs temp_fs;
    ASSERT_TRUE(temp_fs.loadConfig(tst::GetFabricYml()));

    auto [in, out] = tst::CreateInOut();
    // artificial file creation
    const auto name = L"test.dat";

    // check for presence
    std::error_code ec;
    {
        auto [command, result] =
            CheckForUpdateFile(name, L"", UpdateProcess::skip);
        EXPECT_FALSE(result);
    }

    {
        auto [command, result] =
            CheckForUpdateFile(L"invalidname", L"", UpdateProcess::skip);
        EXPECT_FALSE(result);
    }

    {
        auto path = in / name;
        tst::CreateTextFile(path, "-----\n");
        auto [command, result] = CheckForUpdateFile(
            name, in.wstring(), UpdateProcess::skip, out.wstring());
        EXPECT_TRUE(result);

        EXPECT_TRUE(fs::exists(out / name, ec));
        EXPECT_TRUE(!fs::exists(path, ec));

        EXPECT_EQ(command.find(cfg::files::kExecuteUpdateFile),
                  std::string::npos);
    }
    {
        auto path = in / name;
        tst::CreateTextFile(path, "-----\n");

        ASSERT_TRUE(temp_fs.createRootFile(
            fs::path(cfg::dirs::kAgentUtils) / cfg::files::kExecuteUpdateFile,
            "rem echo nothing\n"));
        auto [command, result] = CheckForUpdateFile(
            name, in.wstring(), UpdateProcess::skip, out.wstring());
        EXPECT_TRUE(result);

        EXPECT_TRUE(fs::exists(out / name, ec));
        EXPECT_TRUE(!fs::exists(path, ec));

        EXPECT_NE(command.find(cfg::files::kExecuteUpdateFile),
                  std::string::npos);
    }
}
}  // namespace cma::install
