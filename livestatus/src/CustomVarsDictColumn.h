// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CustomVarsDictColumn_h
#define CustomVarsDictColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <memory>
#include <string>
#include <utility>

#include "Column.h"
#include "Filter.h"
#include "MonitoringCore.h"
#include "opids.h"
class Aggregator;
enum class AttributeKind;
class Row;
class RowRenderer;

#ifdef CMC
#include "contact_fwd.h"
#else
// TODO(sp) Why on earth is "contact_fwd.h" not enough???
#include "nagios.h"
#endif

class CustomVarsDictColumn : public Column {
public:
    CustomVarsDictColumn(std::string name, std::string description,
                         const ColumnOffsets &offsets, const MonitoringCore *mc,
                         AttributeKind kind)
        : Column(std::move(name), std::move(description), offsets)
        , _mc(mc)
        , _kind(kind) {}

    [[nodiscard]] ColumnType type() const override { return ColumnType::dict; };

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;

    [[nodiscard]] virtual Attributes getValue(Row row) const;

private:
    const MonitoringCore *const _mc;
    const AttributeKind _kind;
};

#endif  // CustomVarsDictColumn_h
