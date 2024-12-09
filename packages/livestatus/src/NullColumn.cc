// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/NullColumn.h"

#include <memory>
#include <stdexcept>

#include "livestatus/Renderer.h"
#include "livestatus/Row.h"

void NullColumn::output(Row /*row*/, RowRenderer &r, const User & /*user*/,
                        std::chrono::seconds /*timezone_offset*/) const {
    r.output(Null());
}

std::unique_ptr<Filter> NullColumn::createFilter(
    Filter::Kind /*unused*/, RelationalOperator /*unused*/,
    const std::string & /*unused*/) const {
    throw std::runtime_error("filtering on null column not supported");
}

std::unique_ptr<Sorter> NullColumn::createSorter() const {
    throw std::runtime_error("filtering on null column not supported");
}

std::unique_ptr<Aggregator> NullColumn::createAggregator(
    AggregationFactory /*factory*/) const {
    throw std::runtime_error("aggregating on null column not supported");
}
