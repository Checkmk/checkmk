// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntColumn_h
#define IntColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstdint>
#include <memory>
#include <string>

#include "Column.h"
#include "Filter.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregator;
class Row;
class RowRenderer;

class IntColumn : public Column {
public:
    using Column::Column;

    [[nodiscard]] ColumnType type() const override { return ColumnType::int_; }

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;

    // TODO(sp): The only 2 places where auth_user is actually used are
    // HostListState::getValue() and ServiceListState::getValue().
    // These methods aggregate values for hosts/services, but they should do
    // this only for "allowed" hosts/services. Find a better design than this
    // parameter passing hell..
    virtual int32_t getValue(Row row, const contact *auth_user) const = 0;
};

#endif  // IntColumn_h
