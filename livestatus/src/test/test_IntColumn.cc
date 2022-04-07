// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <initializer_list>
#include <memory>
#include <string>

#include "IntColumn.h"
#include "Row.h"
#include "User.h"
#include "gtest/gtest.h"

using namespace std::string_literals;

struct DummyValue {};

struct DummyRow : Row {
    using Row::Row;
};

TEST(IntColumn, GetValueLambda) {
    const DummyValue val{};
    const DummyRow row{&val};
    User dummy_user{nullptr, ServiceAuthorization::loose,
                    GroupAuthorization::loose};
    for (const auto v : {-42, 0, 1337}) {
        const IntColumn<DummyRow> col{
            "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
                return v;
            }};

        EXPECT_EQ(v, col.getValue(row, dummy_user));
    }
}

TEST(IntColumn, GetValueDefault) {
    const DummyRow row{nullptr};
    User dummy_user{nullptr, ServiceAuthorization::loose,
                    GroupAuthorization::loose};
    for (const auto v : {-42, 0, 1337}) {
        const IntColumn<DummyRow, 123> col{
            "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
                return v;
            }};

        EXPECT_EQ(123, col.getValue(row, dummy_user));
    }
}
