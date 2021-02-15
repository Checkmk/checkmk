// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BoolColumn_h
#define BoolColumn_h

#include <functional>
#include <string>
#include <utility>

#include "IntColumn.h"
#include "contact_fwd.h"
class Row;

template <class T, bool Default = false>
class BoolColumn : public IntColumn {
public:
    BoolColumn(const std::string& name, const std::string& description,
               const ColumnOffsets& offsets, std::function<bool(const T&)> f)
        : IntColumn(name, description, offsets), get_value_{std::move(f)} {}
    ~BoolColumn() override = default;

    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override {
        const T* data = columnData<T>(row);
        return (data == nullptr ? Default : get_value_(*data)) ? 1 : 0;
    }

private:
    std::function<bool(const T&)> get_value_;
};

#endif  // BoolColumn.h
