// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TimeColumn_h
#define TimeColumn_h

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>

#include "Aggregator.h"
#include "Column.h"
#include "Filter.h"
#include "Renderer.h"
#include "Row.h"
#include "TimeAggregator.h"
#include "TimeFilter.h"
#include "opids.h"
class User;

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the start of the epoch.
template <class T>
class TimeColumn : public Column {
public:
    using value_type = std::chrono::system_clock::time_point;

    TimeColumn(const std::string &name, const std::string &description,
               const ColumnOffsets &offsets,
               std::function<value_type(const T &)> f)
        : Column{name, description, offsets}, f_{std::move(f)} {}

    [[nodiscard]] ColumnType type() const override { return ColumnType::time; }

    void output(Row row, RowRenderer &r, const User & /*user*/,
                std::chrono::seconds timezone_offset) const override {
        r.output(getValue(row, timezone_offset));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<TimeFilter>(
            kind, name(),
            [this](Row row, std::chrono::seconds timezone_offset) {
                return this->getValue(row, timezone_offset);
            },
            relOp, value);
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<TimeAggregator>(
            factory, [this](Row row, std::chrono::seconds timezone_offset) {
                return this->getValue(row, timezone_offset);
            });
    }

    [[nodiscard]] value_type getValue(
        Row row, std::chrono::seconds timezone_offset) const {
        const T *data = columnData<T>(row);
        return timezone_offset + (data == nullptr ? value_type{} : f_(*data));
    }

private:
    std::function<value_type(const T &)> f_;
};

#endif
