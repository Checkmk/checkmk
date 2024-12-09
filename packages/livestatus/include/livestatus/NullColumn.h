// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NullColumn_h
#define NullColumn_h

#include <chrono>
#include <string>

#include "livestatus/Column.h"
#include "livestatus/Filter.h"

class NullColumn : public Column {
public:
    using Column::Column;

    [[nodiscard]] ColumnType type() const override { return ColumnType::null; }

    void output(Row row, RowRenderer &r, const User &user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    [[nodiscard]] std::unique_ptr<Sorter> createSorter() const override;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;
};

#endif  // NullColumn_h
