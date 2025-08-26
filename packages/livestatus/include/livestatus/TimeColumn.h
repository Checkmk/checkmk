// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
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
#include <variant>

#include "livestatus/Aggregator.h"
#include "livestatus/Column.h"
#include "livestatus/Filter.h"
#include "livestatus/Renderer.h"
#include "livestatus/Row.h"
#include "livestatus/Sorter.h"
#include "livestatus/TimeAggregator.h"
#include "livestatus/TimeFilter.h"
#include "livestatus/TimeSorter.h"
#include "livestatus/opids.h"
class User;

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the start of the epoch.
template <typename T>
class TimeColumn : public Column {
public:
    using value_type = std::chrono::system_clock::time_point;
    using f0_t = std::function<value_type(const T &)>;
    using f1_t = std::function<value_type(const T &, const ICore &)>;
    using function_type = std::variant<f0_t, f1_t>;

    TimeColumn(const std::string &name, const std::string &description,
               const ColumnOffsets &offsets, function_type f)
        : Column{name, description, offsets}, f_{std::move(f)} {}

    [[nodiscard]] ColumnType type() const override { return ColumnType::time; }

    void output(Row row, RowRenderer &r, const User & /*user*/,
                std::chrono::seconds timezone_offset,
                const ICore &core) const override {
        r.output(getValue(row, timezone_offset, core));
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<TimeFilter>(
            kind, name(),
            [this](Row row, std::chrono::seconds timezone_offset,
                   const ICore &core) {
                return this->getValue(row, timezone_offset, core);
            },
            relOp, value);
    }

    [[nodiscard]] std::unique_ptr<Sorter> createSorter() const override {
        return std::make_unique<TimeSorter>(
            [this](Row row, const std::optional<std::string> &key,
                   std::chrono::seconds timezone_offset, const ICore &core) {
                if (key) {
                    throw std::runtime_error("time column '" + name() +
                                             "' does not expect key '" +
                                             (*key) + "'");
                }
                return getValue(row, timezone_offset, core);
            });
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override {
        return std::make_unique<TimeAggregator>(
            factory, [this](Row row, std::chrono::seconds timezone_offset,
                            const ICore &core) {
                return this->getValue(row, timezone_offset, core);
            });
    }

    [[nodiscard]] value_type getValue(Row row,
                                      std::chrono::seconds timezone_offset,
                                      const ICore &core) const {
        const T *data = columnData<T>(row);
        if (data == nullptr) {
            return timezone_offset + value_type{};
        }
        if (std::holds_alternative<f0_t>(f_)) {
            return timezone_offset + std::get<f0_t>(f_)(*data);
        }
        if (std::holds_alternative<f1_t>(f_)) {
            return timezone_offset + std::get<f1_t>(f_)(*data, core);
        }
        throw std::runtime_error("unreachable");
    }

private:
    function_type f_;
};

#endif
