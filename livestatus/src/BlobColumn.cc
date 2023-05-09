// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "BlobColumn.h"

#include <stdexcept>

#include "Renderer.h"
#include "Row.h"

void detail::BlobColumn::output(
    Row row, RowRenderer& r, const contact* /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    if (std::unique_ptr<std::vector<char>> blob = getValue(row)) {
        r.output(*blob);
    } else {
        r.output(Null());
    }
}

std::unique_ptr<Filter> detail::BlobColumn::createFilter(
    Filter::Kind /*unused*/, RelationalOperator /*unused*/,
    const std::string& /*unused*/) const {
    throw std::runtime_error("filtering on blob column '" + name() +
                             "' not supported");
}

std::unique_ptr<Aggregator> detail::BlobColumn::createAggregator(
    AggregationFactory /*factory*/) const {
    throw std::runtime_error("aggregating on blob column '" + name() +
                             "' not supported");
}
