// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TimeAggregator_h
#define TimeAggregator_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include "Aggregator.h"
#include "TimeColumn.h"
#include "contact_fwd.h"
class Row;
class RowRenderer;

class TimeAggregator : public Aggregator {
public:
    TimeAggregator(const AggregationFactory &factory, const TimeColumn *column)
        : _aggregation(factory()), _column(column) {}

    void consume(Row row, const contact * /*auth_user*/,
                 std::chrono::seconds timezone_offset) override {
        _aggregation->update(std::chrono::system_clock::to_time_t(
            _column->getValue(row, timezone_offset)));
    }

    void output(RowRenderer &r) const override {
        r.output(_aggregation->value());
    }

private:
    std::unique_ptr<Aggregation> _aggregation;
    const TimeColumn *const _column;
};

#endif  // TimeAggregator_h
