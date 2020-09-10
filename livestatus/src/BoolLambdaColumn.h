// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BoolLambdaColumn_h
#define BoolLambdaColumn_h

#include <functional>
#include <string>
#include <utility>

#include "IntColumn.h"
#include "contact_fwd.h"
class Row;

template <class T, bool Default = false>
class BoolLambdaColumn : public IntColumn {
public:
    BoolLambdaColumn(std::string name, std::string description,
                     ColumnOffsets offsets, std::function<bool(const T&)> f)
        : IntColumn(std::move(name), std::move(description), std::move(offsets))
        , get_value_{std::move(f)} {}
    ~BoolLambdaColumn() override = default;

    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override {
        const T* data = columnData<T>(row);
        return (data == nullptr ? Default : get_value_(*data)) ? 1 : 0;
    }

private:
    std::function<bool(const T&)> get_value_;
};

#endif  // BoolLambdaColumn.h
