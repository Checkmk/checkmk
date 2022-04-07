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
#include "auth.h"
#include "contact_fwd.h"
#include "opids.h"
class Row;

template <class T, int32_t Default = 0>
class IntColumn : public Column {
public:
    using value_type = int32_t;
    using f0_t = std::function<value_type(const T &)>;
    using f1_t = std::function<value_type(const T &, const contact *)>;
    using function_type = std::variant<f0_t, f1_t>;

    IntColumn(const std::string &name, const std::string &description,
              const ColumnOffsets &offsets, const function_type &f)
        : Column{name, description, offsets}, f_{f} {}

    [[nodiscard]] ColumnType type() const override { return ColumnType::int_; }

    void output(Row row, RowRenderer &r, const User &user,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(getValue(row, user.authUser()));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<IntFilter>(
            kind, name(),
            [this](Row row, const contact *auth_user) {
                return this->getValue(row, auth_user);
            },
            relOp, value);
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<IntAggregator>(
            factory, [this](Row row, const contact *auth_user) {
                return getValue(row, auth_user);
            });
    }

    // TODO(sp): The only 2 places where auth_user is actually used are
    // HostListState::getValue() and ServiceListState::getValue(). These methods
    // aggregate values for hosts/services, but they should do this only for
    // "allowed" hosts/services. Find a better design than this parameter
    // passing hell..
    [[nodiscard]] virtual value_type getValue(Row row,
                                              const contact *auth_user) const {
        const T *data = IntColumn<T, Default>::template columnData<T>(row);
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

namespace column::detail {
constexpr int32_t toInt32(bool b) { return b ? 1 : 0; }
}  // namespace column::detail

template <class T, bool Default = false>
class BoolColumn : public IntColumn<T, column::detail::toInt32(Default)> {
public:
    BoolColumn(const std::string &name, const std::string &description,
               const ColumnOffsets &offsets, std::function<bool(const T &)> f)
        : IntColumn<T, column::detail::toInt32(Default)>{
              name, description, offsets, [f = std::move(f)](const T &t) {
                  return column::detail::toInt32(f(t));
              }} {}
};

#endif
