// watest.cpp : This file contains the 'main' function. Program execution begins
// and ends there.
//
#include "pch.h"

#include <time.h>

#include <chrono>
#include <filesystem>
#include <future>
#include <string_view>

#include "cfg.h"
#include "cfg_details.h"
#include "cma_core.h"
#include "common/cfg_info.h"
#include "providers/spool.h"
#include "read_file.h"
#include "test_tools.h"

static void CleanFolder(std::filesystem::path Dir) {
    namespace fs = std::filesystem;
    std::error_code ec;

    for (fs::directory_iterator end_dir_it, it(Dir); it != end_dir_it; ++it) {
        fs::remove_all(it->path());
    }
}

static void CreateFileInSpool(const std::filesystem::path& Path,
                              const char* Text) {
    std::ofstream ofs(Path.u8string(), std::ios::binary);

    if (!ofs) {
        XLOG::l("Can't open file {} error {}", Path.u8string(), GetLastError());
        return;
    }

    ofs << Text;
}

// we are using idiotic approach while YAML cannot remove nodes
// reliably. Stupid? Yes!
static void RemoveAllSectionsNodes() {
    using namespace cma::cfg;
    {
        YAML::Node config = cma::cfg::GetLoadedConfig();
        YAML::Emitter out;
        out << YAML::BeginSeq << YAML::Null << YAML::EndSeq;

        config[groups::kGlobal].remove(vars::kSectionsEnabled);
        config[groups::kGlobal].remove(vars::kSectionsDisabled);
    }
}

namespace cma::provider {  // to become friendly for wtools classes
TEST(SectionProviderSpool, Construction) {
    SpoolProvider spool;
    EXPECT_EQ(spool.getUniqName(), cma::section::kSpool);
}

TEST(SectionProviderSpool, BaseApi) {
    namespace fs = std::filesystem;
    fs::path dir = cma::cfg::GetSpoolDir();
    EXPECT_TRUE(cma::provider::IsDirectoryValid(dir));
    EXPECT_FALSE(cma::provider::IsDirectoryValid(dir / "<GTEST>"));

    ASSERT_TRUE(!dir.empty() &&
                dir.u8string().find("\\spool") != std::string::npos);
    CleanFolder(dir);
    ON_OUT_OF_SCOPE(CleanFolder(dir));
    CreateFileInSpool(dir / "0", "");
    EXPECT_FALSE(cma::provider::IsSpoolFileValid(dir / "0"));
    CreateFileInSpool(dir / "1", "");
    ::Sleep(1000);
    EXPECT_FALSE(cma::provider::IsSpoolFileValid(dir / "1"));
    CreateFileInSpool(dir / "99", "");
    EXPECT_TRUE(cma::provider::IsSpoolFileValid(dir / "99"));
    CreateFileInSpool(dir / "99.z", "");
    EXPECT_TRUE(cma::provider::IsSpoolFileValid(dir / "99.z"));

    EXPECT_FALSE(cma::provider::IsSpoolFileValid(dir / "99xxx.z"));
}

TEST(SectionProviderSpool, ReadFiles) {
    namespace fs = std::filesystem;
    ON_OUT_OF_SCOPE(cma::OnStart(cma::AppType::test));

    SpoolProvider spool;
    fs::path dir = cma::cfg::GetSpoolDir();
    ASSERT_TRUE(!dir.empty() &&
                dir.u8string().find("\\spool") != std::string::npos);
    CleanFolder(dir);
    ON_OUT_OF_SCOPE(CleanFolder(dir));

    const char* txt = "aaaa\nbbbb\n";
    CreateFileInSpool(dir / "a.txt", txt);

    const char* txt2 = "0000\n0000\n\n\n\n\n";
    CreateFileInSpool(dir / "0", txt2);

    const char* txt3 = "123456\n9999\n";
    CreateFileInSpool(dir / "99", txt3);
    RemoveAllSectionsNodes();
    tst::EnableSectionsNode(cma::section::kSpool);

    auto ex = spool.generateContent();
    EXPECT_TRUE(!ex.empty());
    auto table = cma::tools::SplitString(ex, "\n");
    EXPECT_EQ(table.size(), 4);
    EXPECT_TRUE(cma::tools::find(table, std::string("aaaa")));
    EXPECT_TRUE(cma::tools::find(table, std::string("bbbb")));
    EXPECT_TRUE(cma::tools::find(table, std::string("123456")));
    EXPECT_TRUE(cma::tools::find(table, std::string("9999")));
}

}  // namespace cma::provider
