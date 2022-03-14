// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <algorithm>
#include <iterator>
#include <string>
#include <vector>

#include "AttributeListColumn.h"
#include "gtest/gtest.h"

namespace a = column::attribute_list;

class AttributeBitTestFixture : public ::testing::TestWithParam<unsigned long> {
protected:
    unsigned long mask;
};

TEST_P(AttributeBitTestFixture, IdentityNumeric) {
    auto mask = GetParam();
    EXPECT_EQ(mask, a::decode(a::encode(mask)));
}

TEST_P(AttributeBitTestFixture, IdentityString) {
    auto mask = GetParam();
    auto bit_v = a::encode(mask);
    std::vector<std::string> strs{};
    std::transform(bit_v.begin(), bit_v.end(), std::back_inserter(strs),
                   column::detail::serialize<a::AttributeBit>);

    EXPECT_EQ(mask, a::decode(a::encode(strs)));
}

INSTANTIATE_TEST_SUITE_P(AttributeBitTests, AttributeBitTestFixture,
                         ::testing::Values(0, 1, 2, 3, 4, 5, 6, 7, 0x8, 0xf,
                                           0xff, 0xfff, 0xffff));

TEST(AttributeBitTest, Encode) {
    std::vector<a::AttributeBit> encoded = a::encode(0b01001001);
    EXPECT_EQ(a::AttributeBit(0, true), encoded[0]);
    EXPECT_EQ(a::AttributeBit(1, false), encoded[1]);
    EXPECT_EQ(a::AttributeBit(2, false), encoded[2]);
    EXPECT_EQ(a::AttributeBit(3, true), encoded[3]);
    EXPECT_EQ(a::AttributeBit(4, false), encoded[4]);
    EXPECT_EQ(a::AttributeBit(5, false), encoded[5]);
    EXPECT_EQ(a::AttributeBit(6, true), encoded[6]);
    EXPECT_EQ(a::AttributeBit(7, false), encoded[7]);
}
