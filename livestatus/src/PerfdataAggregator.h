// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef PerfdataAggregator_h
#define PerfdataAggregator_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include "Aggregator.h"
#include "Column.h"
#include "contact_fwd.h"
class Row;
class RowRenderer;
class StringColumn;

class PerfdataAggregator : public Aggregator {
public:
    PerfdataAggregator(AggregationFactory factory, const StringColumn *column)
        : _factory(std::move(factory)), _column(column) {}
    void consume(Row row, const contact *auth_user,
                 std::chrono::seconds timezone_offset) override;
    void output(RowRenderer &r) const override;

private:
    AggregationFactory _factory;
    const StringColumn *const _column;
    std::map<std::string, std::unique_ptr<Aggregation>> _aggregations;
};

#endif  // PerfdataAggregator_h
