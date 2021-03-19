// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntLambdaColumn_h
#define IntLambdaColumn_h

#include <functional>
#include <string>
#include <utility>
#include <variant>

#include "IntColumn.h"
#include "contact_fwd.h"
class Row;

struct IntColumn : deprecated::IntColumn {
    class Constant;
    class Reference;
    template <class T, int32_t = 0>
    class Callback;

    using deprecated::IntColumn::IntColumn;
    std::int32_t getValue(Row row,
                          const contact* /*auth_user*/) const override = 0;
};

template <class T, int32_t Default>
class IntColumn::Callback : public IntColumn {
    using f0_t = std::function<int(const T&)>;
    using f1_t = std::function<int(const T&, const contact*)>;
    using function_type = std::variant<f0_t, f1_t>;

public:
    Callback(const std::string& name, const std::string& description,
             const ColumnOffsets& offsets, const function_type& f)
        : IntColumn{name, description, offsets}, f_{f} {}
    ~Callback() override = default;

    std::int32_t getValue(Row row, const contact* auth_user) const override {
        const T* data = columnData<T>(row);
        if (std::holds_alternative<f0_t>(f_)) {
            return data == nullptr ? Default : std::get<f0_t>(f_)(*data);
        } else if (std::holds_alternative<f1_t>(f_)) {
            return data == nullptr ? Default
                                   : std::get<f1_t>(f_)(*data, auth_user);
        } else {
            throw std::runtime_error("unreachable");
        }
    }

private:
    const function_type f_;
};

class IntColumn::Constant : public IntColumn {
public:
    Constant(const std::string& name, const std::string& description, int x)
        : IntColumn{name, description, {}}, x_{x} {}
    ~Constant() override = default;

    std::int32_t getValue(Row /*row*/,
                          const contact* /*auth_user*/) const override {
        return x_;
    }

private:
    const std::int32_t x_;
};

class IntColumn::Reference : public IntColumn {
public:
    Reference(const std::string& name, const std::string& description, int& x)
        : IntColumn{name, description, {}}, x_{x} {}
    ~Reference() override = default;

    std::int32_t getValue(Row /*row*/,
                          const contact* /*auth_user*/) const override {
        return x_;
    }

private:
    const std::int32_t& x_;
};

#endif
