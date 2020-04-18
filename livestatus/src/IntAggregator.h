// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntAggregator_h
#define IntAggregator_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include "Aggregator.h"
#include "IntColumn.h"
#include "contact_fwd.h"
class Row;
class RowRenderer;

class IntAggregator : public Aggregator {
public:
    IntAggregator(const AggregationFactory &factory, const IntColumn *column)
        : _aggregation(factory()), _column(column) {}

    void consume(Row row, const contact *auth_user,
                 std::chrono::seconds /* timezone_offset*/) override {
        _aggregation->update(_column->getValue(row, auth_user));
    }

    void output(RowRenderer &r) const override {
        r.output(_aggregation->value());
    }

private:
    std::unique_ptr<Aggregation> _aggregation;
    const IntColumn *const _column;
};

#endif  // IntAggregator_h
