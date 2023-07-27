// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/StatsColumn.h"

#include <stdexcept>
#include <utility>

#include "livestatus/Aggregator.h"
#include "livestatus/AndingFilter.h"
#include "livestatus/CountAggregator.h"
#include "livestatus/Logger.h"

StatsColumnCount::StatsColumnCount(std::unique_ptr<Filter> filter)
    : _filter(std::move(filter)) {}

std::unique_ptr<Filter> StatsColumnCount::stealFilter() {
    return std::move(_filter);
}

std::unique_ptr<Aggregator> StatsColumnCount::createAggregator(
    Logger * /*logger*/) const {
    return std::make_unique<CountAggregator>(_filter.get());
}

// Note: We create an "accept all" filter, just in case we fall back to
// counting.
StatsColumnOp::StatsColumnOp(AggregationFactory factory,
                             std::shared_ptr<Column> column)
    : _factory(std::move(factory))
    , _column(std::move(column))
    , _filter(AndingFilter::make(Filter::Kind::stats, {})) {}

std::unique_ptr<Filter> StatsColumnOp::stealFilter() {
    throw std::runtime_error("not a counting aggregator");
}

std::unique_ptr<Aggregator> StatsColumnOp::createAggregator(
    Logger *logger) const {
    try {
        return _column->createAggregator(_factory);
    } catch (const std::runtime_error &e) {
        Informational(logger) << e.what() << ", falling back to counting";
        return std::make_unique<CountAggregator>(_filter.get());
    }
}
