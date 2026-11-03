// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>

#include "gtest/gtest.h"

using namespace std::chrono;

namespace {
std::string zoneinfo_dir;

std::string write_tzdata(const std::string &name, const std::string &content) {
    auto dir = std::filesystem::path{testing::TempDir()} / name;
    std::filesystem::create_directories(dir);
    std::ofstream{dir / "tzdata.zi"} << content;
    return dir.string();
}
}  // namespace

// libstdc++ reads tzdata.zi from the directory this returns.
namespace __gnu_cxx {
const char *zoneinfo_dir_override() { return zoneinfo_dir.c_str(); }
}  // namespace __gnu_cxx

TEST(TestTzdata, ReadsDebianStyleTzdata) {
    // SUP-31107: libstdc++ 14.2 cannot parse "%z" and discards the whole file.
    zoneinfo_dir = write_tzdata("debian",
                                "# version test-debian\n"
                                "R E 1981 ma - Mar lastSu 1u 1 S\n"
                                "R E 1996 ma - O lastSu 1u 0 -\n"
                                "Z Europe/Berlin 1 E CE%sT\n"
                                "Z Africa/Bissau -1 - %z\n");

    const auto &tzdb = reload_tzdb();
    const auto *berlin = tzdb.locate_zone("Europe/Berlin");

    EXPECT_EQ("test-debian", tzdb.version);
    EXPECT_EQ(1h, berlin->get_info(sys_days{January / 15 / 2026}).offset);
    EXPECT_EQ(2h, berlin->get_info(sys_days{July / 15 / 2026}).offset);
}

TEST(TestTzdata, ReadsUbuntuStyleTzdata) {
    zoneinfo_dir = write_tzdata("ubuntu",
                                "# version test-ubuntu\n"
                                "# dataform rearguard\n"
                                "R E 1981 ma - Mar lastSu 1u 1 S\n"
                                "R E 1996 ma - O lastSu 1u 0 -\n"
                                "Z Europe/Berlin 1 E CE%sT\n"
                                "Z Africa/Bissau -1 - -01\n");

    const auto &tzdb = reload_tzdb();
    const auto *berlin = tzdb.locate_zone("Europe/Berlin");

    EXPECT_EQ("test-ubuntu", tzdb.version);
    EXPECT_EQ(1h, berlin->get_info(sys_days{January / 15 / 2026}).offset);
    EXPECT_EQ(2h, berlin->get_info(sys_days{July / 15 / 2026}).offset);
}

TEST(TestTzdata, UsesBuiltInTzdataWithoutATzdataFile) {
    zoneinfo_dir = std::filesystem::path{testing::TempDir()} / "none";

    const auto &tzdb = reload_tzdb();
    const auto *berlin = tzdb.locate_zone("Europe/Berlin");

    EXPECT_EQ(1h, berlin->get_info(sys_days{January / 15 / 2026}).offset);
    EXPECT_EQ(2h, berlin->get_info(sys_days{July / 15 / 2026}).offset);
}
