// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringColumn_h
#define StringColumn_h

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>

#include "livestatus/Column.h"
#include "livestatus/Filter.h"
#include "livestatus/PerfdataAggregator.h"
#include "livestatus/Sorter.h"
#include "livestatus/StringFilter.h"
#include "livestatus/StringSorter.h"
#include "livestatus/opids.h"
class Aggregator;
class Row;
class RowRenderer;
class User;

// TODO(ml, sp): C++-20 should let us use strings as default template parameter
// (see P0732).
template <typename T>
class StringColumn : public Column {
public:
    StringColumn(const std::string &name, const std::string &description,
                 const ColumnOffsets &offsets,
                 const std::function<std::string(const T &)> &f)
        : Column{name, description, offsets}, f_{f} {}

    [[nodiscard]] ColumnType type() const override {
        return ColumnType::string;
    }

    void output(Row row, RowRenderer &r, const User & /*user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(row.isNull() ? "" : getValue(row));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<StringFilter>(
            kind, name(), [this](Row row) { return this->getValue(row); },
            relOp, value);
    }

    [[nodiscard]] std::unique_ptr<Sorter> createSorter() const override {
        return std::make_unique<StringSorter>(
            [this](Row row, const std::optional<std::string> &key) {
                if (key) {
                    throw std::runtime_error("string column '" + name() +
                                             "' does not expect key '" +
                                             (*key) + "'");
                }
                return getValue(row);
            });
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory /*factory*/) const override {
        throw std::runtime_error("aggregating on string column '" + name() +
                                 "' not supported");
    }

    [[nodiscard]] std::string getValue(Row row) const {
        using namespace std::string_literals;
        const T *data = columnData<T>(row);
        return data == nullptr ? ""s : f_(*data);
    }

private:
    const std::function<std::string(const T &)> f_;
};

template <typename T>
class StringColumnPerfData : public StringColumn<T> {
public:
    using StringColumn<T>::StringColumn;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<PerfdataAggregator>(
            factory, [this](Row row) { return this->getValue(row); });
    }
};

#endif
