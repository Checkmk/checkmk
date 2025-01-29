// Copyright (C) 2019 Checkmk GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <initializer_list>
#include <string>

#include "gtest/gtest.h"
#include "livestatus/ChronoUtils.h"

using namespace std::chrono_literals;

TEST(TestManglingTimestamp, Identity) {
    for (auto d : {0ms, 1234ms, 123456789012ms}) {
        auto t = std::chrono::time_point<std::chrono::system_clock,
                                         std::chrono::microseconds>{d};
        EXPECT_EQ(mk::demangleTimePoint(mk::mangleTimePoint(t)), t);
    }
}

TEST(TestManglingTimestamp, Reproducibility) {
    for (auto d : {0ms, 1234ms, 123456789012ms}) {
        auto t = std::chrono::time_point<std::chrono::system_clock,
                                         std::chrono::microseconds>{d};
        auto x = mk::mangleTimePoint(t);
        EXPECT_EQ(mk::mangleTimePoint(mk::demangleTimePoint(x)), x);
    }
}
