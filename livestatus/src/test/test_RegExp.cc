#include <string>
#include "RegExp.h"
#include "gtest/gtest.h"

TEST(RegExpTest, RespectLiteral) {
    RegExp r{"max", RegExp::Case::respect, RegExp::Syntax::literal};

    EXPECT_EQ("MinGNARK MinKENU", r.replace("maxGNARK maxKENU", "Min"));

    EXPECT_FALSE(r.match("ma"));
    EXPECT_TRUE(r.match("max"));
    EXPECT_FALSE(r.match("GNARK maxKENU"));

    EXPECT_FALSE(r.search("ma"));
    EXPECT_TRUE(r.search("max"));
    EXPECT_TRUE(r.search("GNARK maxKENU"));
}

TEST(RegExpTest, IgnoreLiteral) {
    RegExp r{"MaX", RegExp::Case::ignore, RegExp::Syntax::literal};

    EXPECT_EQ("MinGNARK MinKENU", r.replace("maxGNARK maxKENU", "Min"));

    EXPECT_FALSE(r.match("ma"));
    EXPECT_TRUE(r.match("max"));
    EXPECT_FALSE(r.match("GNARK maxKENU"));

    EXPECT_FALSE(r.search("ma"));
    EXPECT_TRUE(r.search("max"));
    EXPECT_TRUE(r.search("GNARK maxKENU"));
}

TEST(RegExpTest, RespectPattern) {
    RegExp r{"m+.[w-z]", RegExp::Case::respect, RegExp::Syntax::pattern};

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
    RegExp r{"M+.[w-z]", RegExp::Case::ignore, RegExp::Syntax::pattern};

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
    RegExp r{"xy.z|", RegExp::Case::respect, RegExp::Syntax::literal};

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
