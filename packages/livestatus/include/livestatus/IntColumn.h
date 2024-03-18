// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
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

#include "IntAggregator.h"
#include "livestatus/Column.h"
#include "livestatus/Filter.h"
#include "livestatus/IntFilter.h"
#include "livestatus/IntSorter.h"
#include "livestatus/Renderer.h"
#include "livestatus/Sorter.h"
#include "livestatus/User.h"
#include "livestatus/opids.h"
class Row;

template <typename T, int32_t Default = 0>
class IntColumn : public Column {
public:
    using value_type = int32_t;
    using f0_t = std::function<value_type(const T &)>;
    using f1_t = std::function<value_type(const T &, const User &)>;
    using function_type = std::variant<f0_t, f1_t>;

    IntColumn(const std::string &name, const std::string &description,
              const ColumnOffsets &offsets, const function_type &f)
        : Column{name, description, offsets}, f_{f} {}

    [[nodiscard]] ColumnType type() const override { return ColumnType::int_; }

    void output(Row row, RowRenderer &r, const User &user,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(getValue(row, user));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<IntFilter>(
            kind, name(),
            [this](Row row, const User &user) {
                return this->getValue(row, user);
            },
            relOp, value);
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<IntAggregator>(
            factory,
            [this](Row row, const User &user) { return getValue(row, user); });
    }

    [[nodiscard]] std::unique_ptr<Sorter> createSorter() const override {
        return std::make_unique<IntSorter>(
            [this](Row row, const std::optional<std::string> &key,
                   const User &user) {
                if (key) {
                    throw std::runtime_error("int column '" + name() +
                                             "' does not expect key '" +
                                             (*key) + "'");
                }
                return getValue(row, user);
            });
    }

    // TODO(sp): The only 2 places where auth_user is actually used are
    // HostListState::getValue() and ServiceListState::getValue(). These methods
    // aggregate values for hosts/services, but they should do this only for
    // "allowed" hosts/services. Find a better design than this parameter
    // passing hell..
    [[nodiscard]] value_type getValue(Row row, const User &user) const {
        const T *data = IntColumn<T, Default>::template columnData<T>(row);
        if (std::holds_alternative<f0_t>(f_)) {
            return data == nullptr ? Default : std::get<f0_t>(f_)(*data);
        }
        if (std::holds_alternative<f1_t>(f_)) {
            return data == nullptr ? Default : std::get<f1_t>(f_)(*data, user);
        }
        throw std::runtime_error("unreachable");
    }

private:
    const function_type f_;
};

namespace column::detail {
constexpr int32_t toInt32(bool b) { return b ? 1 : 0; }
}  // namespace column::detail

template <typename T, bool Default = false>
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
