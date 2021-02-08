// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TimeColumn.h"

#include "Aggregator.h"
#include "Renderer.h"
#include "Row.h"
#include "TimeAggregator.h"
#include "TimeFilter.h"

void TimeColumn::output(Row row, RowRenderer &r, const contact * /*auth_user*/,
                        std::chrono::seconds timezone_offset) const {
    r.output(getValue(row, timezone_offset));
}

std::unique_ptr<Filter> TimeColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<TimeFilter>(kind, name(),
        [this](Row row, std::chrono::seconds timezone_offset){return this->getValue(row, timezone_offset); }, relOp, value);
}

std::unique_ptr<Aggregator> TimeColumn::createAggregator(
    AggregationFactory factory) const {
    return std::make_unique<TimeAggregator>(
        factory, [this](Row row, std::chrono::seconds timezone_offset) {
            return this->getValue(row, timezone_offset);
        });
}

std::chrono::system_clock::time_point TimeColumn::getValue(
    Row row, std::chrono::seconds timezone_offset) const {
    return getRawValue(row) + timezone_offset;
}
