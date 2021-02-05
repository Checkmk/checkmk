// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the empty string.
template <class T>
class StringColumn : public Column {
public:
    struct Constant;
    struct Reference;
    struct PerfData;
    StringColumn(std::string name, std::string description,
                 ColumnOffsets offsets, std::function<std::string(const T&)> gv)
        : Column(std::move(name), std::move(description), std::move(offsets))
        , get_value_(std::move(gv)) {}

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

    [[nodiscard]] std::string getValue(Row row) const {
        using namespace std::string_literals;
        const T* data = columnData<T>(row);
        return data == nullptr ? ""s : get_value_(*data);
    }

private:
    std::function<std::string(const T&)> get_value_;
};

template <class T>
struct StringColumn<T>::Constant : StringColumn {
    Constant(std::string name, std::string description, const std::string& x)
        : StringColumn(std::move(name), std::move(description), {},
                       [x](const T& /*t*/) { return x; }){};
};

template <class T>
struct StringColumn<T>::Reference : StringColumn {
    Reference(std::string name, std::string description, const std::string& x)
        : StringColumn(std::move(name), std::move(description), {},
                       [&x](const T& /*t*/) { return x; }){};
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
