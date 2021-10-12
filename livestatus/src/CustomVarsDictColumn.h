// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CustomVarsDictColumn_h
#define CustomVarsDictColumn_h

#include "config.h"  // IWYU pragma: keep

#include <memory>
#include <string>
#include <utility>

#include "DictColumn.h"
#include "Filter.h"
#include "opids.h"
enum class AttributeKind;
class Row;
class ColumnOffsets;
class MonitoringCore;

class CustomVarsDictColumn : public DictColumn {
public:
    CustomVarsDictColumn(std::string name, std::string description,
                         const ColumnOffsets &offsets, const MonitoringCore *mc,
                         AttributeKind kind)
        : DictColumn{std::move(name), std::move(description), offsets}
        , _mc(mc)
        , _kind(kind) {}

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    [[nodiscard]] value_type getValue(Row row) const override;

private:
    const MonitoringCore *const _mc;
    const AttributeKind _kind;
};

#endif  // CustomVarsDictColumn_h
