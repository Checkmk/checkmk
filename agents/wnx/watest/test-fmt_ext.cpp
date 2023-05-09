// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "pch.h"

#include <chrono>
#include <filesystem>

#include "common/fmt_ext.h"

TEST(FmtExt, Filesystem) {
    EXPECT_EQ(
        fmt::format("f={}", std::filesystem::path{"c:\\windows\\notepad.EXE"}),
        "f=c:\\windows\\notepad.EXE");
}

TEST(FmtExt, Chrono) {
    EXPECT_EQ(fmt::format("f={}", std::chrono::milliseconds{1}), "f=1ms");
    EXPECT_EQ(fmt::format("f={}", std::chrono::microseconds{2}), "f=2us");
    EXPECT_EQ(fmt::format("f={}", std::chrono::nanoseconds{3}), "f=3ns");
    EXPECT_EQ(fmt::format("f={}", std::chrono::seconds{4}), "f=4s");
}
