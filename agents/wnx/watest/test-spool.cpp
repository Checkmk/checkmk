// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <filesystem>

#include "wnx/cfg.h"
#include "wnx/cma_core.h"
#include "common/cfg_info.h"
#include "providers/spool.h"
#include "watest/test_tools.h"

namespace cma::provider {

TEST(SectionProviderSpool, Construction) {
    SpoolProvider spool;
    EXPECT_EQ(spool.getUniqName(), section::kSpool);
}

TEST(SectionProviderSpool, BaseApiComponent) {
    namespace fs = std::filesystem;
    auto temp_fs{tst::TempCfgFs::Create()};

    fs::path dir = cfg::GetSpoolDir();
    EXPECT_TRUE(provider::IsDirectoryValid(dir));
    EXPECT_FALSE(provider::IsDirectoryValid(dir / "<GTEST>"));

    ASSERT_TRUE(!dir.empty() &&
                wtools::ToStr(dir).find("\\spool") != std::string::npos);

    const fs::path spool_dir{cfg::dirs::kSpool};

    ASSERT_TRUE(temp_fs->createDataFile(spool_dir / "0", ""));
    EXPECT_FALSE(provider::IsSpoolFileValid(dir / "0"));
    ASSERT_TRUE(temp_fs->createDataFile(spool_dir / "1", ""));
    ::Sleep(1000);
    EXPECT_FALSE(provider::IsSpoolFileValid(dir / "1"));

    ASSERT_TRUE(temp_fs->createDataFile(spool_dir / "99", ""));
    EXPECT_TRUE(provider::IsSpoolFileValid(dir / "99"));

    ASSERT_TRUE(temp_fs->createDataFile(spool_dir / "99.z", ""));
    EXPECT_TRUE(provider::IsSpoolFileValid(dir / "99.z"));
    EXPECT_FALSE(provider::IsSpoolFileValid(dir / "99xxx.z"));
}

TEST(SectionProviderSpool, FullComponent) {
    namespace fs = std::filesystem;
    auto temp_fs{tst::TempCfgFs::Create()};
    ASSERT_TRUE(temp_fs->loadConfig(tst::GetFabricYml()));
    auto cfg = cfg::GetLoadedConfig();
    cfg[cfg::groups::kGlobal][cfg::vars::kSectionsEnabled] =
        YAML::Load("[spool]");
    cfg::ProcessKnownConfigGroups();

    SpoolProvider spool;
    const fs::path spool_dir{cfg::dirs::kSpool};

    // assume three files in the spool folder, one of them is expired
    ASSERT_TRUE(temp_fs->createDataFile(spool_dir / "a.txt", "aaaa\nbbbb\n"));

    ASSERT_TRUE(temp_fs->createDataFile(spool_dir / "0",  // <-- expired!
                                        "0000\n0000\n\n\n\n\n"));
    ASSERT_TRUE(temp_fs->createDataFile(spool_dir / "99", "123456\n9999\n"));

    tst::EnableSectionsNode(section::kSpool, true);

    auto ex = spool.generateContent();
    ASSERT_TRUE(!ex.empty());
    auto table = tools::SplitString(ex, "\r\n");
    EXPECT_EQ(table.size(), 4);
    EXPECT_TRUE(std::ranges::find(table, std::string("aaaa")) != table.end());
    EXPECT_TRUE(std::ranges::find(table, std::string("bbbb")) != table.end());
    EXPECT_TRUE(std::ranges::find(table, std::string("123456")) != table.end());
    EXPECT_TRUE(std::ranges::find(table, std::string("9999")) != table.end());
}

}  // namespace cma::provider
