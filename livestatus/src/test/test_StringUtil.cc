// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <bitset>
#include <cstddef>
#include <sstream>
#include <string>
#include <string_view>
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

TEST(StringUtilTest, LStripTest) {
    EXPECT_EQ("", mk::lstrip("  "));
    EXPECT_EQ("xx", mk::lstrip("  \t\n\t  xx"));
    EXPECT_EQ("xx  ", mk::lstrip("  xx  "));
    EXPECT_EQ("xx  xx", mk::lstrip("xx  xx"));
}

TEST(StringUtilTest, EscapeNonprintableTest) {
    {
        std::ostringstream out{};
        out << mk::escape_nonprintable{"\1\xfftoto 42\x7e\x7f\x80"};
        EXPECT_EQ(R"(\x01\xFFtoto 42~\x7F\x80)", out.str());
    }

    {
        std::ostringstream out{};
        out << mk::escape_nonprintable{"\1\2\3"};
        EXPECT_EQ(R"(\x01\x02\x03)", out.str());
    }

    // No UTF-8 support.
    {
        std::ostringstream out{};
        out << mk::escape_nonprintable{"凄くない"};
        EXPECT_EQ(R"(\xE5\x87\x84\xE3\x81\x8F\xE3\x81\xAA\xE3\x81\x84)",
                  out.str());
    }

    {
        std::ostringstream out{};
        out << mk::escape_nonprintable{"Blödsinn"};
        EXPECT_EQ(R"(Bl\xC3\xB6dsinn)", out.str());
    }
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

// https://www.unicode.org/versions/Unicode15.0.0/ch03.pdf p.125
// Correct UTF-8 encoding
// ----------------------------------------------------------------
// Code Points         First Byte Second Byte Third Byte Fourth Byte
// U+0000 -   U+007F     00 - 7F
// U+0080 -   U+07FF     C2 - DF    80 - BF
// U+0800 -   U+0FFF     E0         A0 - BF     80 - BF
// U+1000 -   U+CFFF     E1 - EC    80 - BF     80 - BF
// U+D000 -   U+D7FF     ED         80 - 9F     80 - BF
// U+E000 -   U+FFFF     EE - EF    80 - BF     80 - BF
// U+10000 -  U+3FFFF    F0         90 - BF     80 - BF    80 - BF
// U+40000 -  U+FFFFF    F1 - F3    80 - BF     80 - BF    80 - BF
// U+100000 - U+10FFFF   F4         80 - 8F     80 - BF    80 - BF

TEST(Utf8Test, AsciiIsUtf) {
    EXPECT_TRUE(mk::is_utf8({"\x01"}));
    EXPECT_TRUE(mk::is_utf8({"\x79"}));
}

TEST(Utf8Test, WrongLeadingCharUtf) {
    EXPECT_FALSE(mk::is_utf8({"\x80\x80"}));
    EXPECT_FALSE(mk::is_utf8({"\xC1\x80"}));
    EXPECT_FALSE(mk::is_utf8({"\xF5\x80\x80\x80"}));
    EXPECT_FALSE(mk::is_utf8({"\xFF\x80\x80\x80"}));
}

TEST(Utf8Test, BadUtf) {
    EXPECT_FALSE(mk::is_utf8("\xC2\x7f"));
    EXPECT_FALSE(mk::is_utf8("\xDF\xC0"));
    EXPECT_FALSE(mk::is_utf8("\xE0\x9F\x80"));  // starts A0
    EXPECT_FALSE(mk::is_utf8("\xE0\xBF\xC0"));
    EXPECT_FALSE(mk::is_utf8("\xE1\x80\x7F"));
    EXPECT_FALSE(mk::is_utf8("\xE1\xC0\xBF"));
    EXPECT_FALSE(mk::is_utf8("\xED\x7F\x80"));
    EXPECT_FALSE(mk::is_utf8("\xED\xA0\xBF"));  // ends 9f
    EXPECT_FALSE(mk::is_utf8("\xEF\x7F\x80"));
    EXPECT_FALSE(mk::is_utf8("\xEF\xBF\xC0"));
    // four bytes
    EXPECT_FALSE(mk::is_utf8("\xF0\x8F\x80\x80"));  // starts 90
    EXPECT_FALSE(mk::is_utf8("\xF0\xBF\xC0\xBF"));
    EXPECT_FALSE(mk::is_utf8("\xF1\x7F\x80\x80"));
    EXPECT_FALSE(mk::is_utf8("\xF1\xBF\xBF\xC0"));
    EXPECT_FALSE(mk::is_utf8("\xF2\x80\x7F\x80"));
    EXPECT_FALSE(mk::is_utf8("\xF2\xC0\xBF\xBF"));
    EXPECT_FALSE(mk::is_utf8("\xF4\x80\x80\x7F"));
    EXPECT_FALSE(mk::is_utf8("\xF4\x90\xBF\xBF"));  // ends 8F
}

struct Span {
    std::string_view low;
    std::string_view high;
};

class Utf8Fixture : public ::testing::TestWithParam<std::string_view> {
protected:
    static std::string_view shorten(std::string_view s) {
        return {s.data(), s.length() - 1};
    }
};

TEST_P(Utf8Fixture, GoodUtf8) { EXPECT_TRUE(mk::is_utf8(GetParam())); }

TEST_P(Utf8Fixture, TooShort) {
    EXPECT_FALSE(mk::is_utf8(shorten(GetParam())));
}

INSTANTIATE_TEST_SUITE_P(
    Utf8Test, Utf8Fixture,
    ::testing::Values(
        // two bytes
        "\xC2\x80", "\xDF\xBF",
        // three bytes
        "\xE0\xA0\x80", "\xE0\xBF\xBF", "\xE1\x80\x80", "\xE1\xBF\xBF",
        "\xE2\x80\x80", "\xE2\xBF\xBF", "\xE3\x80\x80", "\xE3\xBF\xBF",
        "\xE4\x80\x80", "\xE4\xBF\xBF", "\xE5\x80\x80", "\xE5\xBF\xBF",
        "\xE6\x80\x80", "\xE6\xBF\xBF", "\xE7\x80\x80", "\xE7\xBF\xBF",
        "\xE8\x80\x80", "\xE8\xBF\xBF", "\xE9\x80\x80", "\xE9\xBF\xBF",
        "\xEA\x80\x80", "\xEA\xBF\xBF", "\xEB\x80\x80", "\xEB\xBF\xBF",
        "\xEC\x80\x80", "\xEC\xBF\xBF", "\xED\x80\x80", "\xED\x9F\xBF",
        "\xEE\x80\x80", "\xEE\xBF\xBF", "\xEF\x80\x80", "\xEF\xBF\xBF",
        // four bytes
        "\xF0\x90\x80\x80", "\xF0\xBF\xBF\xBF", "\xF1\x80\x80\x80",
        "\xF1\xBF\xBF\xBF", "\xF2\x80\x80\x80", "\xF2\xBF\xBF\xBF",
        "\xF3\x80\x80\x80", "\xF3\xBF\xBF\xBF", "\xF4\x80\x80\x80",
        "\xF4\x8F\xBF\xBF"));
