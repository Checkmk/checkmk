// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DoubleAggregator_h
#define DoubleAggregator_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>

#include "Aggregator.h"
#include "Column.h"
class Row;
class RowRenderer;
class User;

class DoubleAggregator : public Aggregator {
public:
    DoubleAggregator(const AggregationFactory &factory,
                     std::function<double(Row)> getValue)
        : _aggregation(factory()), _getValue(std::move(getValue)) {}

    void consume(Row row, const User & /*user*/,
                 std::chrono::seconds /*timezone_offset*/) override {
        _aggregation->update(_getValue(row));
    }

    void output(RowRenderer &r) const override {
        r.output(_aggregation->value());
    }

private:
    std::unique_ptr<Aggregation> _aggregation;
    std::function<double(Row)> _getValue;
};

#endif  // DoubleAggregator_h
