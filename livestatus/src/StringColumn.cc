// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "StringColumn.h"

#include <stdexcept>

#include "Renderer.h"
#include "Row.h"
#include "StringFilter.h"

void StringColumn::output(Row row, RowRenderer &r,
                          const contact * /*auth_user*/,
                          std::chrono::seconds /*timezone_offset*/) const {
    r.output(row.isNull() ? "" : getValue(row));
}

std::unique_ptr<Filter> StringColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<StringFilter>(kind, *this, relOp, value);
}

std::unique_ptr<Aggregator> StringColumn::createAggregator(
    AggregationFactory /*factory*/) const {
    throw std::runtime_error("aggregating on string column '" + name() +
                             "' not supported");
}
