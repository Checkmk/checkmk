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
        zip_file_ = user_dir_ / tst::zip_to_test;
        cab_file_ = user_dir_ / tst::cab_to_test;
    }
    std::unique_ptr<tst::TempDirPair> dirs_;
    fs::path user_dir_;
    fs::path target_;
    fs::path zip_file_;
    fs::path cab_file_;
};

TEST(Zip, ListIntegration) {
    auto ret = List(tst::G_TestPath / tst::cab_to_test);
    ASSERT_TRUE(ret.empty());
    ret = List(tst::G_TestPath / tst::zip_to_test);
    ASSERT_EQ(ret.size(), 5);
}

TEST_F(ZipFixture, UnZipIntegration) {
    auto target = target_ / "unzip";
    auto work_file = zip_file_;

    fs::copy_file(tst::G_TestPath / tst::zip_to_test, work_file);

    ASSERT_FALSE(Extract(work_file / "1", target_));

    ASSERT_FALSE(Extract(work_file, target));
    ASSERT_TRUE(fs::create_directories(target));
    ASSERT_FALSE(Extract(target, work_file));
    ASSERT_FALSE(Extract(target_, work_file));
    ASSERT_FALSE(Extract(target, target));

    //
    auto expected_entries = List(work_file);
    ASSERT_TRUE(Extract(work_file, target));
    for (auto& entry : expected_entries) {
        EXPECT_TRUE(fs::exists(target / entry));
    }
}

TEST_F(ZipFixture, UnCabIntegration) {
    auto target = target_ / "uncab";
    auto work_file = cab_file_;

    fs::copy_file(tst::G_TestPath / tst::cab_to_test, work_file);
    ASSERT_FALSE(Extract((work_file / "1"), target_));

    ASSERT_FALSE(Extract(work_file, target));
    ASSERT_TRUE(fs::create_directories(target));
    ASSERT_FALSE(Extract(target, work_file));
    ASSERT_FALSE(Extract(target_, work_file));
    ASSERT_FALSE(Extract(target, target));
    //
    ASSERT_TRUE(Extract(work_file, target));
    for (auto& entry : {"systemd", "mtr.cfg", "systemd/check_mk.socket"}) {
        EXPECT_TRUE(fs::exists(target / entry));
    }
}
}  // namespace cma::tools::zip
