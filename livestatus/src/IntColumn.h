// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntColumn_h
#define IntColumn_h

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <utility>
#include <variant>

#include "Column.h"
#include "Filter.h"
#include "IntAggregator.h"
#include "IntFilter.h"
#include "Renderer.h"
#include "contact_fwd.h"
#include "opids.h"
class Row;

struct IntColumn : Column {
    using value_type = std::int32_t;
    class Constant;
    class Reference;
    template <class T, value_type = 0>
    class Callback;
    using Column::Column;
    ~IntColumn() override = default;

    // TODO(sp): The only 2 places where auth_user is actually used are
    // HostListState::getValue() and ServiceListState::getValue().
    // These methods aggregate values for hosts/services, but they should do
    // this only for "allowed" hosts/services. Find a better design than this
    // parameter passing hell..
    [[nodiscard]] virtual value_type getValue(
        Row row, const contact* /*auth_user*/) const = 0;
    void output(Row row, RowRenderer& r, const contact* auth_user,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(getValue(row, auth_user));
    }
    [[nodiscard]] ColumnType type() const override { return ColumnType::int_; }
    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
        return std::make_unique<IntFilter>(
            kind, name(),
            [this](Row row, const contact* auth_user) {
                return this->getValue(row, auth_user);
            },
            relOp, value);
    }
    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<IntAggregator>(
            factory, [this](Row row, const contact* auth_user) {
                return getValue(row, auth_user);
            });
    }
};

template <class T, IntColumn::value_type Default>
class IntColumn::Callback : public IntColumn {
    using f0_t = std::function<value_type(const T&)>;
    using f1_t = std::function<value_type(const T&, const contact*)>;

public:
    using function_type = std::variant<f0_t, f1_t>;
    Callback(const std::string& name, const std::string& description,
             const ColumnOffsets& offsets, const function_type& f)
        : IntColumn{name, description, offsets}, f_{f} {}
    ~Callback() override = default;

    value_type getValue(Row row, const contact* auth_user) const override {
        const T* data = columnData<T>(row);
        if (std::holds_alternative<f0_t>(f_)) {
            return data == nullptr ? Default : std::get<f0_t>(f_)(*data);
        }
        if (std::holds_alternative<f1_t>(f_)) {
            return data == nullptr ? Default
                                   : std::get<f1_t>(f_)(*data, auth_user);
        }
        throw std::runtime_error("unreachable");
    }

private:
    const function_type f_;
};

class IntColumn::Constant : public IntColumn {
public:
    Constant(const std::string& name, const std::string& description,
             value_type x)
        : IntColumn{name, description, {}}, x_{x} {}
    ~Constant() override = default;

    value_type getValue(Row /*row*/,
                        const contact* /*auth_user*/) const override {
        return x_;
    }

private:
    const value_type x_;
};

#endif
