// test-section_ps.cpp
//
//
#include "pch.h"

#include "cfg.h"
#include "common/wtools.h"
#include "providers/df.h"

namespace cma::provider {
TEST(DfTest, Bases) {
    {
        auto all_drives = df::GetDriveVector();
        ASSERT_TRUE(!all_drives.empty());
        auto c_disk_found =
            std::any_of(std::begin(all_drives), std::end(all_drives),
                        [](std::string_view drive) {
                            return cma::tools::IsEqual(drive, "c:\\");
                        });
        ASSERT_TRUE(c_disk_found);
    }

    {
        constexpr auto volume_id = "C:\\";
        auto [fs_name, volume_name] = df::GetNamesByVolumeId(volume_id);
        EXPECT_TRUE(fs_name == "NTFS");
        EXPECT_TRUE(!volume_name.empty());

        auto [avail, total] = df::GetSpacesByVolumeId(volume_id);
        EXPECT_TRUE(avail > 0);
        EXPECT_TRUE(avail < total);
    }
}

TEST(DfTest, Integration) {
    {
        constexpr auto volume_id = "C:\\";
        {
            auto fs = df::ProduceFileSystemOutput(volume_id);
            EXPECT_TRUE(!fs.empty());
            if (fs.back() == '\n') fs.pop_back();

            auto table = cma::tools ::SplitString(fs, "\t");
            EXPECT_EQ(table.size(), 7);
            EXPECT_EQ(table[6], volume_id);
        }

        auto mp = df::ProduceMountPointsOutput(volume_id);
        if (mp.empty()) {
            XLOG::SendStringToStdio("Mounting points absent, no checks\n",
                                    XLOG::Colors::yellow);
        } else {
            auto raws = cma::tools ::SplitString(mp, "\n");

            for (auto& raw : raws) {
                auto table = cma::tools ::SplitString(raw, "\t");
                EXPECT_EQ(table.size(), 7);
            }
        }
    }

    {
        auto [fs_name, volume_name] = df::GetNamesByVolumeId("ZX");
        EXPECT_TRUE(fs_name.empty());
        EXPECT_TRUE(volume_name.empty());
        auto [avail, total] = df::GetSpacesByVolumeId("");
        EXPECT_TRUE(avail == 0);
        EXPECT_TRUE(total == 0);
    }

    {
        EXPECT_EQ(0, df::CalcUsage(1, 0));
        EXPECT_EQ(0, df::CalcUsage(0, 0));
        EXPECT_EQ(0, df::CalcUsage(2, 2));
        EXPECT_EQ(50, df::CalcUsage(5, 10));
        EXPECT_EQ(1, df::CalcUsage(99, 100));
    }
}

TEST(DfTest, Full) {
    {
        cma::provider::Df df;
        auto result = df.generateContent(cma::section::kUseEmbeddedName);
        ASSERT_TRUE(!result.empty());

        auto rows = cma::tools::SplitString(result, "\n");
        EXPECT_TRUE(rows.size() > 1);
        EXPECT_EQ(rows[0], "<<<df:sep(9)>>>");
        rows.erase(rows.begin());
        for (auto& r : rows) {
            auto table = cma::tools::SplitString(r, "\t");
            EXPECT_EQ(table.size(), 7);
        }
    }
}

}  // namespace cma::provider
