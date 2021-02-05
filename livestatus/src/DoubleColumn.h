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
#include <ratio>
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

// NOTE: The C++ spec explicitly disallows doubles as non-type template
// parameters. We could add an int or perhaps even some std::ratio if we want.
// Currently the default is hardwired to zero.
template <class T>
class DoubleColumn : public Column {
public:
    DoubleColumn(std::string name, std::string description,
                 ColumnOffsets offsets, std::function<double(const T &)> gv)
        : Column(std::move(name), std::move(description), std::move(offsets))
        , get_value_{std::move(gv)} {}
    ~DoubleColumn() override = default;

    [[nodiscard]] double getValue(Row row) const {
        const T *data = columnData<T>(row);
        return data == nullptr ? 0.0 : get_value_(*data);
    }
    void output(Row row, RowRenderer &r, const contact * /*auth_user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        r.output(getValue(row));
    }
    [[nodiscard]] ColumnType type() const override {
        return ColumnType::double_;
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

private:
    std::function<double(const T &)> get_value_;
};

#endif  // DoubleColumn_h
