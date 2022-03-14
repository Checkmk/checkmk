// test-section_ps.cpp
//
//
#include "pch.h"

#include "cfg.h"
#include "common/wtools.h"
#include "providers/df.h"

namespace cma::provider {

namespace {
constexpr auto g_volume_id_c = "C:\\";
}

TEST(DfTest, GetDriveVector) {
    auto all_drives = df::GetDriveVector();
    ASSERT_TRUE(!all_drives.empty());

    auto c_disk_found = std::any_of(
        std::begin(all_drives), std::end(all_drives),
        [](std::string_view drive) { return tools::IsEqual(drive, "c:\\"); });
    ASSERT_TRUE(c_disk_found);
}

TEST(DfTest, GetNamesByVolumeIdOnC) {
    auto [fs_name, volume_name] = df::GetNamesByVolumeId(g_volume_id_c);
    EXPECT_TRUE(fs_name == "NTFS");
    EXPECT_TRUE(!volume_name.empty());
}
TEST(DfTest, GetSpacesByVolumeIdOnC) {
    auto [avail, total] = df::GetSpacesByVolumeId(g_volume_id_c);
    EXPECT_TRUE(avail > 0);
    EXPECT_TRUE(avail < total);
}

TEST(DfTest, ProduceFileSystemOutput) {
    auto fs = df::ProduceFileSystemOutput(g_volume_id_c);
    EXPECT_TRUE(!fs.empty());
    if (fs.back() == '\n') fs.pop_back();

    auto table = tools ::SplitString(fs, "\t");
    EXPECT_EQ(table.size(), 7);
    EXPECT_EQ(table[6], g_volume_id_c);
}

TEST(DfTest, ProduceMountPointsOutput) {
    auto mp = df::ProduceMountPointsOutput(g_volume_id_c);
    if (mp.empty()) {
        GTEST_SKIP()
            << "Mounting points absent: you have mount at least two different points\n";
        return;
    }

    auto raws = tools::SplitString(mp, "\n");

    std::set<std::string> all;

    for (auto &raw : raws) {
        auto table = tools ::SplitString(raw, "\t");
        EXPECT_EQ(table.size(), 7);
        all.insert(raw);
    }

    EXPECT_EQ(all.size(), raws.size())
        << "Raws has not unique strings, this is quite suspicious\n"
        << mp;
}

TEST(DfTest, GetNamesByVolumeIdOnBad) {
    auto [fs_name, volume_name] = df::GetNamesByVolumeId("ZX");
    EXPECT_TRUE(fs_name.empty());
    EXPECT_TRUE(volume_name.empty());
}

TEST(DfTest, GetSpacesByVolumeIdOnBad) {
    auto [avail, total] = df::GetSpacesByVolumeId("");
    EXPECT_TRUE(avail == 0);
    EXPECT_TRUE(total == 0);
}

TEST(DfTest, CalcUsage) {
    EXPECT_EQ(0, df::CalcUsage(1, 0));
    EXPECT_EQ(0, df::CalcUsage(0, 0));
    EXPECT_EQ(0, df::CalcUsage(2, 2));
    EXPECT_EQ(50, df::CalcUsage(5, 10));
    EXPECT_EQ(1, df::CalcUsage(99, 100));
}

TEST(DfTest, Integration) {
    cma::provider::Df df;
    auto result = df.generateContent();
    ASSERT_TRUE(!result.empty());

    auto rows = tools::SplitString(result, "\n");
    EXPECT_TRUE(rows.size() > 1);
    EXPECT_EQ(rows[0], "<<<df:sep(9)>>>");
    rows.erase(rows.begin());
    for (auto &r : rows) {
        auto table = tools::SplitString(r, "\t");
        EXPECT_EQ(table.size(), 7);
    }
}

}  // namespace cma::provider
