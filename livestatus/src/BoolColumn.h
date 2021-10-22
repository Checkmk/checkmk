// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BoolColumn_h
#define BoolColumn_h

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>

#include "Column.h"
#include "Filter.h"
#include "IntAggregator.h"
#include "IntFilter.h"
#include "Renderer.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"

class Aggregator;
class RowRenderer;

template <class T, bool Default = false>
class BoolColumn : public Column {
public:
    BoolColumn(const std::string& name, const std::string& description,
               const ColumnOffsets& offsets, std::function<bool(const T&)> f)
        : Column{name, description, offsets}, f_{std::move(f)} {}
    ~BoolColumn() override = default;

    [[nodiscard]] ColumnType type() const override { return ColumnType::int_; }

    void output(Row row, RowRenderer& r, const contact* /*auth_user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(getValue(row));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override {
        return std::make_unique<IntFilter>(
            kind, name(), [this](Row row) { return getValue(row); }, relOp,
            value);
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<IntAggregator>(
            factory, [this](Row row) { return getValue(row); });
    }

    std::int32_t getValue(Row row) const {
        const T* data = columnData<T>(row);
        return (data == nullptr ? Default : f_(*data)) ? 1 : 0;
    }

private:
    std::function<bool(const T&)> f_;
};

#endif  // BoolColumn.h
