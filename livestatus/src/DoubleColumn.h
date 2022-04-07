// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DoubleColumn_h
#define DoubleColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>

#include "Aggregator.h"
#include "Column.h"
#include "DoubleAggregator.h"
#include "DoubleFilter.h"
#include "Filter.h"
#include "Renderer.h"
#include "Row.h"
#include "opids.h"
class User;

// NOTE: The C++ spec explicitly disallows doubles as non-type template
// parameters. We could add an int or perhaps even some std::ratio if we want.
// Currently the default is hardwired to zero.
// TODO(ml, sp): C++-20 should let us use double as default template parameter
// (see P0732).
template <class T>
class DoubleColumn : public Column {
public:
    using value_type = double;
    using function_type = std::function<value_type(const T &)>;

    DoubleColumn(const std::string &name, const std::string &description,
                 const ColumnOffsets &offsets, const function_type &f)
        : Column{name, description, offsets}, f_{f} {}

    [[nodiscard]] ColumnType type() const override {
        return ColumnType::double_;
    }

    void output(Row row, RowRenderer &r, const User & /*user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(getValue(row));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<DoubleFilter>(
            kind, name(), [this](Row row) { return this->getValue(row); },
            relOp, value, logger());
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<DoubleAggregator>(
            factory, [this](Row row) { return this->getValue(row); });
    }

    [[nodiscard]] value_type getValue(Row row) const {
        const T *data = columnData<T>(row);
        return data == nullptr ? 0.0 : f_(*data);
    }

private:
    const value_type Default{};
    const function_type f_;
};

#endif  // DoubleColumn_h
