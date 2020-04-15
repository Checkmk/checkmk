// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OffsetPerfdataColumn.h"
#include "Aggregator.h"
#include "PerfdataAggregator.h"

std::unique_ptr<Aggregator> OffsetPerfdataColumn::createAggregator(
    AggregationFactory factory) const {
    return std::make_unique<PerfdataAggregator>(factory, this);
}
