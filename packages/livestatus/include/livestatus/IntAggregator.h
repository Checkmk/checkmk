// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntAggregator_h
#define IntAggregator_h

#include <chrono>
#include <functional>
#include <utility>
#include <variant>

#include "livestatus/Aggregator.h"
#include "livestatus/Column.h"
#include "livestatus/User.h"
class Row;
class RowRenderer;
class User;

class IntAggregator : public Aggregator {
public:
    IntAggregator(const AggregationFactory &factory,
                  std::function<int(Row, const User &)> getValue)
        : _aggregation{factory()}, _getValue{std::move(getValue)} {}

    void consume(Row row, const User &user,
                 std::chrono::seconds /*timezone_offset*/) override {
        _aggregation->update(_getValue(row, user));
    }

    void output(RowRenderer &r) const override {
        r.output(_aggregation->value());
    }

private:
    std::unique_ptr<Aggregation> _aggregation;
    const std::function<int(Row, const User &)> _getValue;
};

#endif  // IntAggregator_h
