// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntLambdaColumn_h
#define IntLambdaColumn_h

#include <functional>
#include <string>
#include <utility>

#include "IntColumn.h"
#include "contact_fwd.h"
class Row;

namespace detail {
struct IntColumn : ::IntColumn {
    class Constant;
    class Reference;
    using ::IntColumn::IntColumn;
    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override = 0;
};
}  // namespace detail

template <class T, int32_t Default = 0>
class IntLambdaColumn : public detail::IntColumn {
public:
    using ::detail::IntColumn::Constant;
    using ::detail::IntColumn::Reference;
    IntLambdaColumn(const std::string& name, const std::string& description,
                    const ColumnOffsets& offsets,
                    std::function<int(const T&)> gv)
        : detail::IntColumn(name, description, offsets)
        , get_value_{std::move(gv)} {}
    ~IntLambdaColumn() override = default;

    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override {
        const T* data = columnData<T>(row);
        return data == nullptr ? Default : get_value_(*data);
    }

private:
    std::function<int(const T&)> get_value_;
};

class detail::IntColumn::Constant : public detail::IntColumn {
public:
    Constant(std::string name, std::string description, int x)
        : detail::IntColumn(std::move(name), std::move(description), {})
        , x{x} {}

    std::int32_t getValue(Row /*row*/,
                          const contact* /*auth_user*/) const override {
        return x;
    }

private:
    const std::int32_t x;
};

class detail::IntColumn::Reference : public detail::IntColumn {
public:
    Reference(std::string name, std::string description, int& x)
        : detail::IntColumn(std::move(name), std::move(description), {})
        , x{x} {}

    std::int32_t getValue(Row /*row*/,
                          const contact* /*auth_user*/) const override {
        return x;
    }

private:
    const std::int32_t& x;
};

#endif
