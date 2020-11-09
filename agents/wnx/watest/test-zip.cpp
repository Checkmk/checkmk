//
// zip test functions
// requires special zip file in location
//

#include "pch.h"

#include <filesystem>

#include "test_tools.h"
#include "zip.h"

namespace cma::tools::zip {
TEST(CmaTools, Zip) {
    namespace fs = std::filesystem;
    cma::OnStartTest();  // to get temporary folder
    fs::path user_dir = cma::cfg::GetUserDir();
    auto zip_file = user_dir / tst::zip_to_test;
    ASSERT_TRUE(fs::exists(zip_file))
        << "Please make '" << tst::zip_to_test << "' available in the '"
        << user_dir.u8string() << "'";
    //
    tst::SafeCleanTempDir();
    auto [tgt, _] = tst::CreateInOut();
    ON_OUT_OF_SCOPE(tst::SafeCleanTempDir());
    ASSERT_FALSE(Extract((zip_file / "1").wstring(), tgt.wstring()));

    ASSERT_FALSE(Extract(zip_file.wstring(), (tgt / "tst").wstring()));
    ASSERT_TRUE(fs::create_directories(tgt / "tst"));
    ASSERT_FALSE(Extract((tgt / "tst").wstring(), zip_file.wstring()));
    ASSERT_FALSE(Extract(tgt.wstring(), zip_file.wstring()));
    ASSERT_FALSE(Extract((tgt / "tst").wstring(), (tgt / "tst").wstring()));
    auto ret = List(zip_file.wstring());
    ASSERT_EQ(ret.size(), 5);
    //
    ASSERT_TRUE(Extract(zip_file.wstring(), (tgt / "tst").wstring()));
    for (auto& entry : ret) {
        EXPECT_TRUE(fs::exists(tgt / "tst" / entry));
    }
}
}  // namespace cma::tools::zip
