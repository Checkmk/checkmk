// test-service.cpp

//
#include "pch.h"

#include <filesystem>
#include <fstream>

#include "common/wtools.h"
#include "install_api.h"
#include "service_processor.h"
#include "test_tools.h"

namespace cma::install {

TEST(InstallAuto, FileControlIntegration) {
    namespace fs = std::filesystem;
    cma::OnStart(cma::AppType::test);

    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    auto [in, out] = tst::CreateInOut();
    // artificial file creation
    const auto name = L"test.dat";
    auto path = in / name;

    // api functions have to fail
    EXPECT_TRUE(RmFile(path));
    EXPECT_FALSE(MvFile(path, out / name));
    EXPECT_NO_THROW(BackupFile(path, out));
    EXPECT_FALSE(NeedInstall(path, out));

    tst::ConstructFile(path, "-----\n");

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
    tst::ConstructFile(path, "-----\n");
    EXPECT_TRUE(MvFile(path, out / name)) << "move has to success";

    EXPECT_NO_THROW(BackupFile(path, out));
    BackupFile(out / name, in);  // opposite direction, just check that works
    EXPECT_TRUE(fs::exists(path, ec));

    EXPECT_FALSE(NeedInstall(path, out));
    tst::ConstructFile(path, "-----\n");
    EXPECT_TRUE(NeedInstall(path, out));
    BackupFile(path, out);
    EXPECT_FALSE(NeedInstall(path, out));
}

TEST(InstallAuto, GlobalSettings) {
    EXPECT_EQ(GetInstallMode(), InstallMode::normal);
}
TEST(InstallAuto, PrepareExecution) {
    namespace fs = std::filesystem;

    fs::path script_log_file(cfg::GetLogDir());
    script_log_file /= "execute_script.log";

    fs::path script_file(cfg::GetRootUtilsDir());
    script_file /= cfg::files::kExecuteUpdateFile;

    auto [command, msi_log_file] =
        PrepareExecution(L"msi exec", L"x x x", false);
    auto expected_cmd_line = fmt::format(
        LR"("{}" "msi exec" "/i x x x /qn /L*V {}" "{}")",
        script_file.wstring(), msi_log_file, script_log_file.wstring());
    EXPECT_EQ(command, expected_cmd_line);

    EXPECT_EQ(fs::path(msi_log_file).filename().u8string(), kMsiLogFileName);
}

extern bool g_use_script_to_install;
TEST(InstallAuto, PrepareExecutionLegacy) {
    namespace fs = std::filesystem;
    g_use_script_to_install = false;
    ON_OUT_OF_SCOPE(g_use_script_to_install = true);

    EXPECT_EQ(GetInstallMode(), InstallMode::normal);

    auto [command, msi_log_file] =
        PrepareExecution(L"msi-exec", L"xx.msi", false);
    EXPECT_EQ(command,
              fmt::format(LR"(msi-exec /i xx.msi /qn /L*V {})", msi_log_file));

    EXPECT_EQ(fs::path(msi_log_file).filename().u8string(), kMsiLogFileName);
}

TEST(InstallAuto, PrepareExecutionFallback) {
    namespace fs = std::filesystem;
    ASSERT_TRUE(g_use_script_to_install);

    EXPECT_EQ(GetInstallMode(), InstallMode::normal);

    auto [command, msi_log_file] =
        PrepareExecution(L"msi-exec", L"xx.msi", true);
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
        tst::ConstructFile(path, "-----\n");
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
        tst::ConstructFile(path, "-----\n");

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
