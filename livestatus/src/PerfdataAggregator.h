// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef PerfdataAggregator_h
#define PerfdataAggregator_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <utility>

#include "Aggregator.h"
#include "Column.h"
class Row;
class RowRenderer;
class User;

class PerfdataAggregator : public Aggregator {
public:
    PerfdataAggregator(AggregationFactory factory,
                       std::function<std::string(Row)> getValue)
        : _factory(std::move(factory)), _getValue{std::move(getValue)} {}
    void consume(Row row, const User &user,
                 std::chrono::seconds timezone_offset) override;
    void output(RowRenderer &r) const override;

private:
    AggregationFactory _factory;
    const std::function<std::string(Row)> _getValue;
    std::map<std::string, std::unique_ptr<Aggregation>> _aggregations;
};

#endif  // PerfdataAggregator_h
