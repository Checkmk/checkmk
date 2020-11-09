// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ListColumn.h"

#include <stdexcept>

#include "ListFilter.h"
#include "Renderer.h"
#include "Row.h"

void ListColumn::output(Row row, RowRenderer &r, const contact *auth_user,
                        std::chrono::seconds timezone_offset) const {
    ListRenderer l(r);
    for (const auto &val : getValue(row, auth_user, timezone_offset)) {
        l.output(val);
    }
}

std::unique_ptr<Filter> ListColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<ListFilter>(kind, *this, relOp, value);
}

std::unique_ptr<Aggregator> ListColumn::createAggregator(
    AggregationFactory /*factory*/) const {
    throw std::runtime_error("aggregating on list column '" + name() +
                             "' not supported");
}
