// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef OffsetPerfdataColumn_h
#define OffsetPerfdataColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include "Column.h"
#include "OffsetStringColumn.h"
class Aggregator;

class OffsetPerfdataColumn : public OffsetStringColumn {
public:
    using OffsetStringColumn::OffsetStringColumn;
    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;
};

#endif  // OffsetPerfdataColumn_h
