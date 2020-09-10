// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DoubleLambdaColumn_h
#define DoubleLambdaColumn_h

#include <functional>
#include <ratio>
#include <string>
#include <utility>

#include "DoubleColumn.h"
class Row;

// NOTE: The C++ spec explicitly disallows doubles as non-type template
// parameters. We could add an int or perhaps even some std::ratio if we want.
// Currently the default is hardwired to zero.
template <class T>
class DoubleLambdaColumn : public DoubleColumn {
public:
    DoubleLambdaColumn(std::string name, std::string description,
                       ColumnOffsets offsets,
                       std::function<double(const T&)> gv)
        : DoubleColumn(std::move(name), std::move(description),
                       std::move(offsets))
        , get_value_{std::move(gv)} {}

    ~DoubleLambdaColumn() override = default;

    [[nodiscard]] double getValue(Row row) const override {
        const T* data = columnData<T>(row);
        return data == nullptr ? 0.0 : get_value_(*data);
    }

private:
    std::function<double(const T&)> get_value_;
};

#endif
