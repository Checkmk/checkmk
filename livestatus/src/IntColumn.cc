// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "IntColumn.h"

#include "Aggregator.h"
#include "IntAggregator.h"
#include "IntFilter.h"
#include "Renderer.h"
#include "Row.h"

void IntColumn::output(Row row, RowRenderer &r, const contact *auth_user,
                       std::chrono::seconds /*timezone_offset*/) const {
    r.output(getValue(row, auth_user));
}

std::unique_ptr<Filter> IntColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<IntFilter>(kind, *this, relOp, value);
}

std::unique_ptr<Aggregator> IntColumn::createAggregator(
    AggregationFactory factory) const {
    return std::make_unique<IntAggregator>(factory, this);
}
