// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CustomVarsDictColumn.h"

#include <stdexcept>

#include "CustomVarsDictFilter.h"
#include "Renderer.h"
#include "Row.h"
class Aggregator;

#ifdef CMC
#include "cmc.h"
#endif

void CustomVarsDictColumn::output(
    Row row, RowRenderer &r, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    DictRenderer d(r);
    for (const auto &it : getValue(row)) {
        d.output(it.first, it.second);
    }
}

std::unique_ptr<Filter> CustomVarsDictColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<CustomVarsDictFilter>(kind, *this, relOp, value);
}

std::unique_ptr<Aggregator> CustomVarsDictColumn::createAggregator(
    AggregationFactory /*factory*/) const {
    throw std::runtime_error("aggregating on dictionary column '" + name() +
                             "' not supported");
}

Attributes CustomVarsDictColumn::getValue(Row row) const {
    if (const auto *p = columnData<void>(row)) {
        return _mc->customAttributes(p, _kind);
    }
    return {};
}
