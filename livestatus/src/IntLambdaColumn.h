// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
    using f0_t = std::function<int(const T&)>;
    using f1_t = std::function<int(const T&, const contact*)>;
    using function_type = std::variant<f0_t, f1_t>;

public:
    using ::detail::IntColumn::Constant;
    using ::detail::IntColumn::Reference;
    IntLambdaColumn(const std::string& name, const std::string& description,
                    const ColumnOffsets& offsets, const function_type& f)
        : detail::IntColumn{name, description, offsets}, f_{f} {}
    ~IntLambdaColumn() override = default;

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

class detail::IntColumn::Constant : public detail::IntColumn {
public:
    Constant(const std::string& name, const std::string& description, int x)
        : detail::IntColumn{name, description, {}}, x_{x} {}
    ~Constant() override = default;

    std::int32_t getValue(Row /*row*/,
                          const contact* /*auth_user*/) const override {
        return x_;
    }

private:
    const std::int32_t x_;
};

class detail::IntColumn::Reference : public detail::IntColumn {
public:
    Reference(const std::string& name, const std::string& description, int& x)
        : detail::IntColumn{name, description, {}}, x_{x} {}
    ~Reference() override = default;

    std::int32_t getValue(Row /*row*/,
                          const contact* /*auth_user*/) const override {
        return x_;
    }

private:
    const std::int32_t& x_;
};

#endif
