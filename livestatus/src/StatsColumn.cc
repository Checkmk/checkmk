// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "StatsColumn.h"
#include <ostream>
#include <stdexcept>
#include <utility>
#include "Aggregator.h"
#include "AndingFilter.h"
#include "Column.h"
#include "CountAggregator.h"
#include "Filter.h"
#include "Logger.h"

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
StatsColumnOp::StatsColumnOp(AggregationFactory factory, Column *column)
    : _factory(std::move(factory))
    , _column(column)
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
