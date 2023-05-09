// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
#include "contact_fwd.h"
#include "opids.h"

namespace detail {
class DoubleColumn : public Column {
public:
    class Constant;
    class Reference;
    using Column::Column;
    ~DoubleColumn() override = default;

    [[nodiscard]] virtual double getValue(Row row) const = 0;
    void output(Row row, RowRenderer& r, const contact* /*auth_user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(getValue(row));
    }
    [[nodiscard]] ColumnType type() const override {
        return ColumnType::double_;
    }
    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
        return std::make_unique<DoubleFilter>(
            kind, name(), [this](Row row) { return this->getValue(row); },
            relOp, value, logger());
    }
    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<DoubleAggregator>(
            factory, [this](Row row) { return this->getValue(row); });
    }
};
}  // namespace detail

// NOTE: The C++ spec explicitly disallows doubles as non-type template
// parameters. We could add an int or perhaps even some std::ratio if we want.
// Currently the default is hardwired to zero.
// TODO(ml, sp): C++-20 should let us use double as default
// template parameter (see P0732).
template <class T>
class DoubleColumn : public ::detail::DoubleColumn {
public:
    using ::detail::DoubleColumn::Constant;
    using ::detail::DoubleColumn::Reference;
    DoubleColumn(const std::string& name, const std::string& description,
                 const ColumnOffsets& offsets,
                 const std::function<double(const T&)>& f)
        : detail::DoubleColumn{name, description, offsets}, f_{f} {}
    ~DoubleColumn() override = default;
    [[nodiscard]] double getValue(Row row) const override {
        const T* data = columnData<T>(row);
        return data == nullptr ? 0.0 : f_(*data);
    }

private:
    const std::function<double(const T&)> f_;
};

class detail::DoubleColumn::Constant : public detail::DoubleColumn {
public:
    Constant(const std::string& name, const std::string& description, double x)
        : detail::DoubleColumn{name, description, {}}, x_{x} {}
    ~Constant() override = default;
    double getValue(Row /*row*/) const override { return x_; }

private:
    const double x_;
};

class detail::DoubleColumn::Reference : public detail::DoubleColumn {
public:
    Reference(const std::string& name, const std::string& description,
              double& x)
        : detail::DoubleColumn{name, description, {}}, x_{x} {}
    ~Reference() override = default;
    double getValue(Row /*row*/) const override { return x_; }

private:
    const double& x_;
};

#endif  // DoubleColumn_h
