// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <algorithm>
#include <compare>
#include <initializer_list>
#include <ranges>
#include <string>
#include <string_view>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/StringUtils.h"

using namespace std::string_view_literals;
using mk::natural_compare;

namespace stl = std::ranges;

TEST(NaturalCompareTest, EqualStrings) {
    EXPECT_EQ(natural_compare(""sv, ""sv), std::strong_ordering::equal);
    EXPECT_EQ(natural_compare("host1"sv, "host1"sv),
              std::strong_ordering::equal);
}

TEST(NaturalCompareTest, EmptyIsSmallest) {
    EXPECT_EQ(natural_compare(""sv, "a"sv), std::strong_ordering::less);
    EXPECT_EQ(natural_compare("a"sv, ""sv), std::strong_ordering::greater);
}

TEST(NaturalCompareTest, PlainLexicographic) {
    EXPECT_EQ(natural_compare("apple"sv, "banana"sv),
              std::strong_ordering::less);
    EXPECT_EQ(natural_compare("banana"sv, "apple"sv),
              std::strong_ordering::greater);
    EXPECT_EQ(natural_compare("ab"sv, "abc"sv), std::strong_ordering::less);
}

TEST(NaturalCompareTest, CaseInsensitive) {
    EXPECT_EQ(natural_compare("Host"sv, "host"sv), std::strong_ordering::equal);
    EXPECT_EQ(natural_compare("ABC"sv, "abc"sv), std::strong_ordering::equal);
    // The classic complaint: byte order puts 'Z' (0x5A) before 'a' (0x61);
    // natural order folds case, so 'a' < 'z'.
    EXPECT_EQ(natural_compare("apple"sv, "Zebra"sv),
              std::strong_ordering::less);
    EXPECT_EQ(natural_compare("Zebra"sv, "apple"sv),
              std::strong_ordering::greater);
}

TEST(NaturalCompareTest, DigitRunsCompareNumerically) {
    EXPECT_EQ(natural_compare("host2"sv, "host10"sv),
              std::strong_ordering::less);
    EXPECT_EQ(natural_compare("host10"sv, "host2"sv),
              std::strong_ordering::greater);
    EXPECT_EQ(natural_compare("item9"sv, "item123"sv),
              std::strong_ordering::less);
    EXPECT_EQ(natural_compare("9"sv, "10"sv), std::strong_ordering::less);
    EXPECT_EQ(natural_compare("10"sv, "9"sv), std::strong_ordering::greater);
}

TEST(NaturalCompareTest, LeadingZerosIgnoredForValue) {
    EXPECT_EQ(natural_compare("7"sv, "007"sv), std::strong_ordering::equal);
    EXPECT_EQ(natural_compare("host07"sv, "host7"sv),
              std::strong_ordering::equal);
    EXPECT_EQ(natural_compare("host007x"sv, "host7y"sv),
              std::strong_ordering::less);
}

TEST(NaturalCompareTest, LongDigitRunsNoOverflow) {
    EXPECT_EQ(
        natural_compare("100000000000000000000"sv, "99999999999999999999"sv),
        std::strong_ordering::greater);
}

TEST(NaturalCompareTest, MixedSegmentBoundaries) {
    // num_split("abc")=("abc",) vs num_split("ab1")=("ab",1,"")
    EXPECT_EQ(natural_compare("abc"sv, "ab1"sv), std::strong_ordering::greater);
    EXPECT_EQ(natural_compare("ab1"sv, "abc"sv), std::strong_ordering::less);
    // num_split("a1")=("a",1,"") vs num_split("ab")=("ab",)
    EXPECT_EQ(natural_compare("a1"sv, "ab"sv), std::strong_ordering::less);
    EXPECT_EQ(natural_compare("ab"sv, "a1"sv), std::strong_ordering::greater);
}

TEST(NaturalCompareTest, SortsLikeNumSplit) {
    std::vector values{"host10"sv, "Host2"sv, "host1"sv,
                       "host20"sv, "host3"sv, "HOST10"sv};
    stl::sort(values, [](std::string_view a, std::string_view b) {
        return natural_compare(a, b) == std::strong_ordering::less;
    });
    EXPECT_TRUE(
        stl::equal(values | std::views::take(3),
                   std::initializer_list{"host1"sv, "Host2"sv, "host3"sv}));
    // "host10" and "HOST10" compare equal, so their order is unspecified.
    EXPECT_TRUE((values[3] == "host10"sv && values[4] == "HOST10"sv) ||
                (values[3] == "HOST10"sv && values[4] == "host10"sv));
    EXPECT_EQ(values.back(), "host20"sv);
}
