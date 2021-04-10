// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <bitset>
#include <cstddef>
#include <sstream>
#include <string>
#include <vector>

#include "StringUtils.h"
#include "gtest/gtest.h"

TEST(StringUtilTest, StartsWith) {
    EXPECT_TRUE(mk::starts_with("", ""));

    EXPECT_TRUE(mk::starts_with("foo", ""));
    EXPECT_FALSE(mk::starts_with("", "foo"));

    EXPECT_TRUE(mk::starts_with("foo", "foo"));
    EXPECT_FALSE(mk::starts_with("foo", "fox"));
    EXPECT_FALSE(mk::starts_with("foo", "too"));

    EXPECT_TRUE(mk::starts_with("foobar", "foo"));
    EXPECT_FALSE(mk::starts_with("foo", "foobar"));
}

TEST(StringUtilTest, EndsWith) {
    EXPECT_TRUE(mk::ends_with("", ""));

    EXPECT_TRUE(mk::ends_with("foo", ""));
    EXPECT_FALSE(mk::ends_with("", "foo"));

    EXPECT_TRUE(mk::ends_with("foo", "foo"));
    EXPECT_FALSE(mk::ends_with("foo", "fox"));
    EXPECT_FALSE(mk::ends_with("foo", "too"));

    EXPECT_FALSE(mk::ends_with("foobar", "foo"));
    EXPECT_TRUE(mk::ends_with("foobar", "bar"));
    EXPECT_FALSE(mk::ends_with("foo", "foobar"));
}

TEST(StringUtilTest, JoinTest) {
    using v = std::vector<std::string>;
    EXPECT_EQ("", mk::join(v{}, ", "));
    EXPECT_EQ("foo", mk::join(v{"foo"}, ", "));
    EXPECT_EQ("foo, bar", mk::join(v{"foo", "bar"}, ", "));
    EXPECT_EQ("foo, , bar", mk::join(v{"foo", "", "bar"}, ", "));
}

TEST(StringUtilTest, ReplaceFirstTest) {
    EXPECT_EQ("", mk::replace_first("", "", ""));
    EXPECT_EQ("", mk::replace_first("", "", "|"));
    EXPECT_EQ("", mk::replace_first("", "", "hurz"));

    EXPECT_EQ("", mk::replace_first("", "xy", ""));
    EXPECT_EQ("", mk::replace_first("", "xy", "|"));
    EXPECT_EQ("", mk::replace_first("", "xy", "hurz"));

    EXPECT_EQ("very lovely test we have",
              mk::replace_first("very lovely test we have", "", ""));
    EXPECT_EQ("|very lovely test we have",
              mk::replace_first("very lovely test we have", "", "|"));
    EXPECT_EQ("hurzvery lovely test we have",
              mk::replace_first("very lovely test we have", "", "hurz"));

    EXPECT_EQ("ry lovely test we have",
              mk::replace_first("very lovely test we have", "ve", ""));
    EXPECT_EQ("|ry lovely test we have",
              mk::replace_first("very lovely test we have", "ve", "|"));
    EXPECT_EQ("hurzry lovely test we have",
              mk::replace_first("very lovely test we have", "ve", "hurz"));

    EXPECT_EQ("very lovely test we have",
              mk::replace_first("very lovely test we have", "xy", ""));
    EXPECT_EQ("very lovely test we have",
              mk::replace_first("very lovely test we have", "xy", "|"));
    EXPECT_EQ("very lovely test we have",
              mk::replace_first("very lovely test we have", "xy", "hurz"));
}

TEST(StringUtilTest, ReplaceAllTest) {
    EXPECT_EQ("", mk::replace_all("", "", ""));
    EXPECT_EQ("|", mk::replace_all("", "", "|"));
    EXPECT_EQ("hurz", mk::replace_all("", "", "hurz"));

    EXPECT_EQ("", mk::replace_all("", "xy", ""));
    EXPECT_EQ("", mk::replace_all("", "xy", "|"));
    EXPECT_EQ("", mk::replace_all("", "xy", "hurz"));

    EXPECT_EQ("very lovely test we have",
              mk::replace_all("very lovely test we have", "", ""));
    EXPECT_EQ("|v|e|r|y| |l|o|v|e|l|y| |t|e|s|t| |w|e| |h|a|v|e|",
              mk::replace_all("very lovely test we have", "", "|"));
    EXPECT_EQ(
        "hurzvhurzehurzrhurzyhurz hurzlhurzohurzvhurzehurzlhurzyhurz hurz"
        "thurzehurzshurzthurz hurzwhurzehurz hurzhhurzahurzvhurzehurz",
        mk::replace_all("very lovely test we have", "", "hurz"));

    EXPECT_EQ("ry loly test we ha",
              mk::replace_all("very lovely test we have", "ve", ""));
    EXPECT_EQ("|ry lo|ly test we ha|",
              mk::replace_all("very lovely test we have", "ve", "|"));
    EXPECT_EQ("hurzry lohurzly test we hahurz",
              mk::replace_all("very lovely test we have", "ve", "hurz"));

    EXPECT_EQ("very lovely test we have",
              mk::replace_all("very lovely test we have", "xy", ""));
    EXPECT_EQ("very lovely test we have",
              mk::replace_all("very lovely test we have", "xy", "|"));
    EXPECT_EQ("very lovely test we have",
              mk::replace_all("very lovely test we have", "xy", "hurz"));
}

TEST(StringUtilTest, FromMultiLine) {
    EXPECT_EQ("", mk::from_multi_line(""));
    EXPECT_EQ("foo bar", mk::from_multi_line("foo bar"));
    EXPECT_EQ("\\nfoo\\nbar\\n", mk::from_multi_line("\nfoo\nbar\n"));
    EXPECT_EQ("\\nfoo\\nbar\\n", mk::from_multi_line("\\nfoo\\nbar\\n"));
}

TEST(StringUtilTest, ToMultiLine) {
    EXPECT_EQ("", mk::to_multi_line(""));
    EXPECT_EQ("foo bar", mk::to_multi_line("foo bar"));
    EXPECT_EQ("\nfoo\nbar\n", mk::to_multi_line("\nfoo\nbar\n"));
    EXPECT_EQ("\nfoo\nbar\n", mk::to_multi_line("\\nfoo\\nbar\\n"));
}

namespace {
template <size_t N>
std::string format_bitset(const std::bitset<N> &bs) {
    std::ostringstream os;
    os << FormattedBitSet<N>{bs};
    return os.str();
}
}  // namespace

TEST(StringUtilTest, FormattedBitSet) {
    EXPECT_EQ("{}", format_bitset<8>(0b00000000));
    EXPECT_EQ("{0}", format_bitset<8>(0b00000001));
    EXPECT_EQ("{7}", format_bitset<8>(0b10000000));
    EXPECT_EQ("{1, 2, 4, 5, 7}", format_bitset<8>(0b10110110));
}
