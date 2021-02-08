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
#include "contact_fwd.h"
#include "opids.h"

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the start of the epoch.
template <class T>
class TimeColumn : public Column {
public:
    struct Constant;
    struct Reference;
    TimeColumn(
        std::string name, std::string description, ColumnOffsets offsets,
        std::function<std::chrono::system_clock::time_point(const T&)> gv)
        : Column(std::move(name), std::move(description), std::move(offsets))
        , get_value_{std::move(gv)} {}

    ~TimeColumn() override = default;

    [[nodiscard]] ColumnType type() const override { return ColumnType::time; }

    void output(Row row, RowRenderer& r, const contact* /*auth_user*/,
                std::chrono::seconds timezone_offset) const override {
        r.output(getValue(row, timezone_offset));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
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

    [[nodiscard]] std::chrono::system_clock::time_point getValue(
        Row row, std::chrono::seconds timezone_offset) const {
        return getRawValue(row) + timezone_offset;
    }

private:
    [[nodiscard]] std::chrono::system_clock::time_point getRawValue(
        Row row) const {
        const T* data = columnData<T>(row);
        return data == nullptr ? std::chrono::system_clock::time_point{}
                               : get_value_(*data);
    }

    std::function<std::chrono::system_clock::time_point(const T&)> get_value_;
};

template <class T>
struct TimeColumn<T>::Constant : TimeColumn {
    Constant(std::string name, std::string description,
             std::chrono::system_clock::time_point x)
        : TimeColumn(std::move(name), std::move(description), {},
                     [x](const T& /*t*/) { return x; }){};
};

template <class T>
struct TimeColumn<T>::Reference : TimeColumn {
    Reference(std::string name, std::string description,
              std::chrono::system_clock::time_point& x)
        : TimeColumn(std::move(name), std::move(description), {},
                     [&x](const T& /*t*/) { return x; }){};
};

#endif
