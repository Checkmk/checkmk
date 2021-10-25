// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <string>
#include <vector>

#include "ListColumn.h"
#include "Row.h"
#include "gtest/gtest.h"

using namespace std::chrono_literals;
using namespace std::string_literals;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST(ListColumn, GetValueLambda) {
    auto v = ListColumn::value_type{"hello"s, "world"s};

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = ListColumnCallback<DummyRow, std::string>{
        "name"s, "description"s, {}, [v](const DummyRow& /*row*/) {
            return v;
        }};

    EXPECT_EQ(v, col.getValue(row, nullptr, 0s));
}

TEST(ListColumn, GetValueDefault) {
    auto v = ListColumn::value_type{"hello"s, "world"s};

    const auto row = DummyRow{nullptr};
    const auto col = ListColumnCallback<DummyRow, std::string>{
        "name"s, "description"s, {}, [v](const DummyRow& /*row*/) {
            return v;
        }};

    EXPECT_NE(v, col.getValue(row, nullptr, 0s));
    EXPECT_EQ(ListColumn::value_type{}, col.getValue(row, nullptr, 0s));
}
