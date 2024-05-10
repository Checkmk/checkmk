// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DictColumn_h
#define DictColumn_h

#include <chrono>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>

#include "livestatus/Column.h"
#include "livestatus/DictFilter.h"
#include "livestatus/DoubleSorter.h"
#include "livestatus/Filter.h"
#include "livestatus/Renderer.h"
#include "livestatus/Row.h"
#include "livestatus/Sorter.h"
#include "livestatus/StringSorter.h"
#include "livestatus/opids.h"
enum class AttributeKind;
class Aggregator;
class RowRenderer;
class User;

template <typename T>
class DictStrValueColumn : public Column {
public:
    using value_type = std::unordered_map<std::string, std::string>;
    using function_type = std::function<value_type(const T &)>;

    DictStrValueColumn(const std::string &name, const std::string &description,
                       const ColumnOffsets &offsets, const function_type &f)
        : Column{name, description, offsets}, f_{f} {}

    [[nodiscard]] ColumnType type() const override {
        return ColumnType::dictstr;
    }

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
        return std::make_unique<DictStrValueFilter>(
            kind, this->name(), [this](Row row) { return this->getValue(row); },
            relOp, value);
    }

    [[nodiscard]] std::unique_ptr<Sorter> createSorter() const override {
        return std::make_unique<StringSorter>(
            [this](Row row, const std::optional<std::string> &key) {
                if (!key) {
                    throw std::runtime_error("ordering on dictionary column '" +
                                             name() +
                                             "' requires a dictionary key");
                }
                const auto map = this->getValue(row);
                const auto iter = map.find(*key);
                return iter != map.end() ? iter->second : std::string{};
            });
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

template <typename T>
class DictDoubleValueColumn : public Column {
public:
    using value_type = std::unordered_map<std::string, double>;
    using function_type = std::function<value_type(const T &)>;

    DictDoubleValueColumn(const std::string &name,
                          const std::string &description,
                          const ColumnOffsets &offsets, const function_type &f)
        : Column{name, description, offsets}, f_{f} {}

    [[nodiscard]] ColumnType type() const override {
        return ColumnType::dictdouble;
    }

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
        return std::make_unique<DictDoubleValueFilter>(
            kind, this->name(), [this](Row row) { return this->getValue(row); },
            relOp, value, logger());
    }

    [[nodiscard]] std::unique_ptr<Sorter> createSorter() const override {
        return std::make_unique<DoubleSorter>(
            [this](Row row, const std::optional<std::string> &key) {
                if (!key) {
                    throw std::runtime_error("ordering on dictionary column '" +
                                             name() +
                                             "' requires a dictionary key");
                }
                const auto map = this->getValue(row);
                const auto iter = map.find(*key);
                return iter != map.end() ? iter->second : 0.0;
            });
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
