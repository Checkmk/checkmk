// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <functional>
#include <initializer_list>
#include <memory>
#include <string>

#include "IntColumn.h"
#include "Row.h"
#include "gtest/gtest.h"

using namespace std::string_literals;

struct DummyValue {};

struct DummyRow : Row {
    using Row::Row;
};

TEST(BoolColumn, GetValueLambda) {
    const DummyValue val{};
    const DummyRow row{&val};
    for (const auto v : {false, true}) {
        const BoolColumn<DummyRow> col{
            "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
                return v;
            }};

        EXPECT_EQ(v ? 1 : 0, col.getValue(row, nullptr));
    }
}

TEST(BoolColumn, GetValueDefault) {
    const DummyRow row{nullptr};
    for (const auto v : {false, true}) {
        const BoolColumn<DummyRow, true> col{
            "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
                return v;
            }};

        EXPECT_EQ(1, col.getValue(row, nullptr));
    }
}
