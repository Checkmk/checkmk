// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <optional>
#include <string>

#include "gtest/gtest.h"
#include "livestatus/ChronoUtils.h"

using namespace std::chrono_literals;

TEST(ChronoUtils, CheckedFromTimeTAcceptsTheEpoch) {
    const auto tp = mk::checked_from_time_t(0);

    EXPECT_EQ(std::chrono::system_clock::time_point{}, tp);
}

TEST(ChronoUtils, CheckedFromTimeTAcceptsTheLastRepresentableSecond) {
    const auto tp = mk::checked_from_time_t(9'223'372'036);

    EXPECT_EQ(std::chrono::system_clock::time_point{9'223'372'036s}, tp);
}

TEST(ChronoUtils, CheckedFromTimeTRejectsTimestampsAfter2262) {
    const auto tp = mk::checked_from_time_t(9'223'372'037);

    EXPECT_EQ(std::nullopt, tp);
}

TEST(ChronoUtils, CheckedFromTimeTRejectsNegativeTimestamps) {
    const auto tp = mk::checked_from_time_t(-1);

    EXPECT_EQ(std::nullopt, tp);
}
