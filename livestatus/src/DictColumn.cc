// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DictColumn.h"

#include <stdexcept>
#include <utility>

#include "Renderer.h"

void DictColumn::output(Row row, RowRenderer &r, const contact * /*auth_user*/,
                        std::chrono::seconds /*timezone_offset*/) const {
    DictRenderer d(r);
    for (const auto &it : getValue(row)) {
        d.output(it.first, it.second);
    }
}

std::unique_ptr<Aggregator> DictColumn::createAggregator(
    AggregationFactory /*factory*/) const {
    throw std::runtime_error("aggregating on dictionary column '" + name() +
                             "' not supported");
}
