//
// zip test functions
// requires special zip file in location
//

#include "pch.h"

#include <filesystem>

#include "test_tools.h"
#include "zip.h"
namespace fs = std::filesystem;

namespace cma::tools::zip {

class ZipFixture : public ::testing::Test {
protected:
    void SetUp() override {
        dirs_ = std::make_unique<tst::TempDirPair>(
            ::testing::UnitTest::GetInstance()->current_test_info()->name());
        user_dir_ = dirs_->in();
        target_ = dirs_->out();
        zip_file_ = user_dir_ / tst::install_cab_to_test;
        cab_file_ = user_dir_ / tst::cab_to_test;
    }
    std::unique_ptr<tst::TempDirPair> dirs_;
    fs::path user_dir_;
    fs::path target_;
    fs::path zip_file_;
    fs::path cab_file_;
};

TEST_F(ZipFixture, UnZipIntegration) {
    auto target = target_ / "unzip";
    auto work_file = zip_file_;

    fs::copy_file(tst::GetUnitTestFilesRoot() / tst::install_cab_to_test,
                  work_file);

    ASSERT_FALSE(Extract(work_file / "1", target_));

    ASSERT_FALSE(Extract(work_file, target));
    ASSERT_TRUE(fs::create_directories(target));
    ASSERT_FALSE(Extract(target, work_file));
    ASSERT_FALSE(Extract(target_, work_file));
    ASSERT_FALSE(Extract(target, target));
}

TEST_F(ZipFixture, UnCabIntegration) {
    auto target = target_ / "uncab";
    auto work_file = cab_file_;

    fs::copy_file(tst::GetUnitTestFilesRoot() / tst::cab_to_test, work_file);
    ASSERT_FALSE(Extract((work_file / "1"), target_));

    ASSERT_FALSE(Extract(work_file, target));
    ASSERT_TRUE(fs::create_directories(target));
    ASSERT_FALSE(Extract(target, work_file));
    ASSERT_FALSE(Extract(target_, work_file));
    ASSERT_FALSE(Extract(target, target));
    //
    ASSERT_TRUE(Extract(work_file, target));
    for (auto &entry : {"systemd", "mtr.cfg", "systemd/check_mk.socket"}) {
        EXPECT_TRUE(fs::exists(target / entry));
    }
}
}  // namespace cma::tools::zip
