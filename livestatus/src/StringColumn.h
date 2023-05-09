// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringColumn_h
#define StringColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>

#include "Column.h"
#include "Filter.h"
#include "PerfdataAggregator.h"
#include "StringFilter.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregator;
class Row;
class RowRenderer;

namespace detail {
struct StringColumn : ::Column {
    class Constant;
    class Reference;
    using ::Column::Column;
    ~StringColumn() override = default;

    [[nodiscard]] ColumnType type() const override {
        return ColumnType::string;
    }

    void output(Row row, RowRenderer& r, const contact* /*auth_user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(row.isNull() ? "" : getValue(row));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
        return std::make_unique<StringFilter>(
            kind, name(), [this](Row row) { return this->getValue(row); },
            relOp, value);
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory /*factory*/) const override {
        throw std::runtime_error("aggregating on string column '" + name() +
                                 "' not supported");
    }

    [[nodiscard]] virtual std::string getValue(Row row) const = 0;
};
}  // namespace detail

// TODO(ml, sp): C++-20 should let us use strings as default
// template parameter (see P0732).
template <class T>
class StringColumn : public ::detail::StringColumn {
public:
    using ::detail::StringColumn::Constant;
    using ::detail::StringColumn::Reference;
    struct PerfData;

    StringColumn(const std::string& name, const std::string& description,
                 const ColumnOffsets& offsets,
                 const std::function<std::string(const T&)>& f)
        : detail::StringColumn{name, description, offsets}, f_{f} {}
    ~StringColumn() override = default;

    [[nodiscard]] std::string getValue(Row row) const override {
        using namespace std::string_literals;
        const T* data = columnData<T>(row);
        return data == nullptr ? ""s : f_(*data);
    }

private:
    const std::function<std::string(const T&)> f_;
};

class detail::StringColumn::Constant : public detail::StringColumn {
public:
    // NOTE: clangd-11 and cppcheck disagree, shut up cppcheck >:-)
    Constant(const std::string& name, const std::string& description,
             // cppcheck-suppress passedByValue
             std::string x)
        : detail::StringColumn{name, description, {}}, x_{std::move(x)} {}
    ~Constant() override = default;

    [[nodiscard]] std::string getValue(Row /*row*/) const override {
        return x_;
    }

private:
    const std::string x_;
};

class detail::StringColumn::Reference : public detail::StringColumn {
public:
    Reference(const std::string& name, const std::string& description,
              const std::string& x)
        : detail::StringColumn{name, description, {}}, x_{x} {}
    ~Reference() override = default;
    [[nodiscard]] std::string getValue(Row /*row*/) const override {
        return x_;
    }

private:
    const std::string& x_;
};

template <class T>
struct StringColumn<T>::PerfData : StringColumn {
    using StringColumn<T>::StringColumn;
    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<PerfdataAggregator>(
            factory, [this](Row row) { return this->getValue(row); });
    }
};

#endif
