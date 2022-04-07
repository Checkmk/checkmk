// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DictColumn_h
#define DictColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>

#include "Column.h"
#include "DictFilter.h"
#include "Filter.h"
#include "Renderer.h"
#include "Row.h"
#include "opids.h"
enum class AttributeKind;
class Aggregator;
class RowRenderer;
class User;

template <class T>
class DictColumn : public Column {
public:
    using value_type = std::unordered_map<std::string, std::string>;
    using function_type = std::function<value_type(const T &)>;

    DictColumn(const std::string &name, const std::string &description,
               const ColumnOffsets &offsets, const function_type &f)
        : Column{name, description, offsets}, f_{f} {}

    [[nodiscard]] ColumnType type() const override { return ColumnType::dict; }

    void output(Row row, RowRenderer &r, const User & /*user*/,
                std::chrono::seconds /*timezone_offset*/) const override {
        DictRenderer d(r);
        for (const auto &it : getValue(row)) {
            d.output(it.first, it.second);
        }
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<DictFilter>(
            kind, this->name(), [this](Row row) { return this->getValue(row); },
            relOp, value);
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory /*factory*/) const override {
        throw std::runtime_error("aggregating on dictionary column '" + name() +
                                 "' not supported");
    }

    value_type getValue(Row row) const {
        const T *data = columnData<T>(row);
        return data == nullptr ? value_type{} : f_(*data);
    };

private:
    function_type f_;
};

#endif
