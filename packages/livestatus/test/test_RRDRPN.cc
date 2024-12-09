// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <string>
#include <utility>
#include <vector>

#include "gtest/gtest.h"
#include "livestatus/RRDRPN.h"
#include "livestatus/StringUtils.h"

namespace {
auto split(const std::string &x) { return mk::split(x, ','); }
auto solve(const std::vector<std::string> &x,
           const std::pair<std::string, double> &value) {
    return rrd_rpn_solve(x, value);
}
}  // namespace

TEST(TestRPN, ArithmeticOp) {
    // See https://oss.oetiker.ch/rrdtool/tut/rpntutorial.en.html
    auto two = std::make_pair("two", 2);
    EXPECT_DOUBLE_EQ(6.0, solve(split("1,2,3,+,+"), two));
    EXPECT_DOUBLE_EQ(9.0, solve(split("3,2,1,+,*"), two));
    EXPECT_DOUBLE_EQ(9.0, solve(split("3,2,1,+,*"), two));

    EXPECT_DOUBLE_EQ(2.0, solve(split("two"), two));
    EXPECT_DOUBLE_EQ(6.0, solve(split("1,two,3,+,+"), two));
    EXPECT_DOUBLE_EQ(7.0, solve(split("3,two,*,1,+"), two));
    EXPECT_DOUBLE_EQ(9.0, solve(split("3,two,1,+,*"), two));
    EXPECT_DOUBLE_EQ(4.0, solve(split("two,two,+"), two));

    EXPECT_DOUBLE_EQ(4.5, solve(split("9,2,/"), two));
    EXPECT_DOUBLE_EQ(-2.0, solve(split("8,10,-"), two));
}
