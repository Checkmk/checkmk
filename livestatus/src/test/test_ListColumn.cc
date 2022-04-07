// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <chrono>
#include <memory>
#include <string>
#include <vector>

#include "ListColumn.h"
#include "Row.h"
#include "auth.h"
#include "gtest/gtest.h"

using namespace std::chrono_literals;
using namespace std::string_literals;

struct DummyRow : Row {
    using Row::Row;
};

struct DummyValue {};

TEST(ListColumn, GetValueLambda) {
    using value_type = ListColumn<DummyRow>::value_type;
    value_type v{"hello"s, "world"s};

    const auto val = DummyValue{};
    const auto row = DummyRow{&val};
    const auto col = ListColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
            return v;
        }};
    User dummy_user{nullptr, ServiceAuthorization::loose,
                    GroupAuthorization::loose};

    EXPECT_EQ(v, col.getValue(row, dummy_user, 0s));
}

TEST(ListColumn, GetValueDefault) {
    using value_type = ListColumn<DummyRow>::value_type;
    value_type v{"hello"s, "world"s};

    const auto row = DummyRow{nullptr};
    const auto col = ListColumn<DummyRow>{
        "name"s, "description"s, {}, [v](const DummyRow & /*row*/) {
            return v;
        }};
    User dummy_user{nullptr, ServiceAuthorization::loose,
                    GroupAuthorization::loose};

    EXPECT_NE(v, col.getValue(row, dummy_user, 0s));
    EXPECT_EQ(value_type{}, col.getValue(row, dummy_user, 0s));
}
