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
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregator;
class RowRenderer;

struct BoolColumn : Column {
    template <class T, bool = false>
    class Callback;

    using Column::Column;
    ~BoolColumn() override = default;

    [[nodiscard]] ColumnType type() const override { return ColumnType::int_; }

    void output(Row row, RowRenderer& r, const contact* auth_user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;

    virtual std::int32_t getValue(Row row) const = 0;
};

template <class T, bool Default>
class BoolColumn::Callback : public BoolColumn {
public:
    Callback(const std::string& name, const std::string& description,
             const ColumnOffsets& offsets, std::function<bool(const T&)> f)
        : BoolColumn{name, description, offsets}, f_{std::move(f)} {}
    ~Callback() override = default;

    std::int32_t getValue(Row row) const override {
        const T* data = columnData<T>(row);
        return (data == nullptr ? Default : f_(*data)) ? 1 : 0;
    }

private:
    std::function<bool(const T&)> f_;
};

#endif  // BoolColumn.h
