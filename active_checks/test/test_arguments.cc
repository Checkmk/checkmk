// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <optional>
#include <string>

#include "active_checks/arguments.h"
#include "gtest/gtest.h"

using check_mkevents::parse_number;

TEST(ParseNumber, MaximumIsAccepted) {
    const auto number = parse_number("3600", 3600);

    EXPECT_EQ(number, std::optional<unsigned long>{3600});
}

TEST(ParseNumber, LeadingZerosDontCountEvenBeyondTheDigitsOfTheMaximum) {
    const auto number = parse_number("00001", 3600);

    EXPECT_EQ(number, std::optional<unsigned long>{1});
}

class InvalidNumber : public testing::TestWithParam<std::string> {};

TEST_P(InvalidNumber, IsRejected) {
    const auto number = parse_number(GetParam(), 3600);

    EXPECT_EQ(number, std::nullopt);
}

INSTANTIATE_TEST_SUITE_P(ParseNumber, InvalidNumber,
                         testing::Values("", "0", "abc", "+2", " 2", "2 ", "-1",
                                         "3601"));
