// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntSorter_h
#define IntSorter_h

#include <functional>
#include <utility>

#include "Row.h"
#include "Sorter.h"

class User;

class IntSorter : public Sorter {
    using callback_t = std::function<int(
        Row, const std::optional<std::string> &, const User &)>;

public:
    explicit IntSorter(callback_t getValue) : getValue_{std::move(getValue)} {}
    [[nodiscard]] Sorter::key_type getKey(
        Row row, const std::optional<std::string> &key, const User &user,
        std::chrono::seconds /*timezone_offset*/) const override {
        return getValue_(row, key, user);
    }

private:
    callback_t getValue_;
};

#endif
