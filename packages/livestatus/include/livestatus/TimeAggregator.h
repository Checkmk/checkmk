// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TimeAggregator_h
#define TimeAggregator_h

#include <chrono>

#include "livestatus/Aggregator.h"
#include "livestatus/Column.h"

class Row;
class RowRenderer;

class TimeAggregator : public Aggregator {
public:
    using function_type = std::function<std::chrono::system_clock::time_point(
        Row, std::chrono::seconds, const ICore &)>;

    TimeAggregator(const AggregationFactory &factory, function_type getValue)
        : _aggregation(factory()), _getValue{std::move(getValue)} {}

    void consume(Row row, const User & /*user*/,
                 std::chrono::seconds timezone_offset,
                 const ICore &core) override {
        _aggregation->update(double(std::chrono::system_clock::to_time_t(
            _getValue(row, timezone_offset, core))));
    }

    void output(RowRenderer &r) const override {
        r.output(_aggregation->value());
    }

private:
    std::unique_ptr<Aggregation> _aggregation;
    const function_type _getValue;
};

#endif  // TimeAggregator_h
