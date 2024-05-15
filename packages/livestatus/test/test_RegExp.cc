// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <cstddef>
#include <string>

#include "gtest/gtest.h"
#include "livestatus/RegExp.h"

TEST(RegExpTest, RespectLiteral) {
    const RegExp r{"max", RegExp::Case::respect, RegExp::Syntax::literal};

    EXPECT_EQ("MinGNARK MinKENU", r.replace("maxGNARK maxKENU", "Min"));

    EXPECT_FALSE(r.match("ma"));
    EXPECT_TRUE(r.match("max"));
    EXPECT_FALSE(r.match("GNARK maxKENU"));

    EXPECT_FALSE(r.search("ma"));
    EXPECT_TRUE(r.search("max"));
    EXPECT_TRUE(r.search("GNARK maxKENU"));
}

TEST(RegExpTest, IgnoreLiteral) {
    const RegExp r{"MaX", RegExp::Case::ignore, RegExp::Syntax::literal};

    EXPECT_EQ("MinGNARK MinKENU", r.replace("maxGNARK maxKENU", "Min"));

    EXPECT_FALSE(r.match("ma"));
    EXPECT_TRUE(r.match("max"));
    EXPECT_FALSE(r.match("GNARK maxKENU"));

    EXPECT_FALSE(r.search("ma"));
    EXPECT_TRUE(r.search("max"));
    EXPECT_TRUE(r.search("GNARK maxKENU"));
}

TEST(RegExpTest, RespectPattern) {
    const RegExp r{"m+.[w-z]", RegExp::Case::respect, RegExp::Syntax::pattern};

    EXPECT_EQ("MinGNARK MinKENU", r.replace("maxGNARK maxKENU", "Min"));
    EXPECT_EQ("MinGNARK MinKENU", r.replace("mmmmmczGNARK mbwKENU", "Min"));

    EXPECT_FALSE(r.match("ma"));
    EXPECT_TRUE(r.match("max"));
    EXPECT_TRUE(r.match("mmbz"));
    EXPECT_FALSE(r.match("GNARK maxKENU"));

    EXPECT_FALSE(r.search("ma"));
    EXPECT_TRUE(r.search("max"));
    EXPECT_TRUE(r.search("mmbz"));
    EXPECT_TRUE(r.search("GNARK maxKENU"));
    EXPECT_TRUE(r.search("GNARK mmbz"));
}

TEST(RegExpTest, IgnorePattern) {
    const RegExp r{"M+.[w-z]", RegExp::Case::ignore, RegExp::Syntax::pattern};

    EXPECT_EQ("MinGNARK MinKENU", r.replace("maxGNARK maxKENU", "Min"));
    EXPECT_EQ("MinGNARK MinKENU", r.replace("mmmmmczGNARK mbwKENU", "Min"));
    EXPECT_EQ("MinGNARK MinKENU", r.replace("mMmmmcZGNARK mMMbWKENU", "Min"));

    EXPECT_FALSE(r.match("ma"));
    EXPECT_TRUE(r.match("maX"));
    EXPECT_TRUE(r.match("mMbZ"));
    EXPECT_FALSE(r.match("GNARK maxKENU"));

    EXPECT_FALSE(r.search("ma"));
    EXPECT_TRUE(r.search("max"));
    EXPECT_TRUE(r.search("mMbZ"));
    EXPECT_TRUE(r.search("GNARK maxKENU"));
    EXPECT_TRUE(r.search("GNARK mMbZKENU"));
}

TEST(RegExpTest, CMK1381) {
    // Regression test for wrong quoting of special characters
    const RegExp r{"xy.z|", RegExp::Case::respect, RegExp::Syntax::literal};

    EXPECT_EQ("MinGNARK MinKENU", r.replace("xy.z|GNARK xy.z|KENU", "Min"));
    EXPECT_EQ("MinGNARK xyaz|KENU", r.replace("xy.z|GNARK xyaz|KENU", "Min"));

    EXPECT_FALSE(r.match("xy."));
    EXPECT_TRUE(r.match("xy.z|"));
    EXPECT_FALSE(r.match("xyaz|"));
    EXPECT_FALSE(r.match("GNARK xy.z|KENU"));

    EXPECT_FALSE(r.search("xy."));
    EXPECT_TRUE(r.search("xy.z|"));
    EXPECT_FALSE(r.search("xyaz|"));
    EXPECT_TRUE(r.search("GNARK xy.z|KENU"));
}

TEST(RegExpTest, NullCharacter) {
    using namespace std::literals::string_literals;
    auto s = "foo \x00 bar"s;
    ASSERT_EQ(size_t{9}, s.size());  // just to be sure...
    const RegExp r{s, RegExp::Case::respect, RegExp::Syntax::literal};

    EXPECT_FALSE(r.match("foo "s));
    EXPECT_TRUE(r.match("foo \x00 bar"s));
    EXPECT_FALSE(r.match("xfoo \x00 bary"s));

    EXPECT_FALSE(r.search("foo "s));
    EXPECT_TRUE(r.search("foo \x00 bar"s));
    EXPECT_TRUE(r.search("xfoo \x00 bary"s));
}
