// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DoubleColumn.h"

#include "Aggregator.h"
#include "DoubleAggregator.h"
#include "DoubleFilter.h"
#include "Renderer.h"
#include "Row.h"

void DoubleColumn::output(Row row, RowRenderer &r,
                          const contact * /*auth_user*/,
                          std::chrono::seconds /*timezone_offset*/) const {
    r.output(getValue(row));
}

std::unique_ptr<Filter> DoubleColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<DoubleFilter>(kind, *this, relOp, value);
}

std::unique_ptr<Aggregator> DoubleColumn::createAggregator(
    AggregationFactory factory) const {
    return std::make_unique<DoubleAggregator>(
        factory, [this](Row row) { return this->getValue(row); });
}
