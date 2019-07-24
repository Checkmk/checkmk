// test-service.cpp

//
#include "pch.h"

#include <filesystem>
#include <fstream>

#include "common/wtools.h"
#include "install_api.h"
#include "service_processor.h"
#include "test_tools.h"

TEST(InstallAuto, LowLevel) {
    using namespace cma::install;
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

TEST(InstallAuto, TopLevel) {
    cma::OnStart(cma::AppType::test);
    using namespace cma::install;
    using namespace cma::tools;
    namespace fs = std::filesystem;
    auto msi = cma::cfg::GetMsiExecPath();
    ASSERT_TRUE(!msi.empty());
    tst::SafeCleanTempDir();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());

    auto [in, out] = tst::CreateInOut();
    // artificial file creation
    const auto name = L"test.dat";
    auto path = in / name;
    tst::ConstructFile(path, "-----\n");

    // check for presence
    std::error_code ec;
    auto ret = fs::exists(path, ec);
    ASSERT_TRUE(ret);

    // check MakTemp...
    auto to_install = MakeTempFileNameInTempPath(name);
    EXPECT_TRUE(!to_install.empty());
    {
        auto result = CheckForUpdateFile(name, in.wstring(), (UpdateType)535,
                                         UpdateProcess::skip);
        EXPECT_FALSE(result);

        result = CheckForUpdateFile(name, L"", UpdateType::exec_quiet,
                                    UpdateProcess::skip);
        EXPECT_FALSE(result);

        result = CheckForUpdateFile(L"invalidname", L"", UpdateType::exec_quiet,
                                    UpdateProcess::skip);
        EXPECT_FALSE(result);

        result = CheckForUpdateFile(name, in.wstring(), UpdateType::exec_quiet,
                                    UpdateProcess::skip, out.wstring());
        EXPECT_TRUE(result);

        EXPECT_TRUE(fs::exists(to_install, ec));
        EXPECT_TRUE(fs::exists(out / name, ec));
        EXPECT_TRUE(!fs::exists(path, ec));
    }
}
