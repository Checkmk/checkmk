// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "AttributeListColumn.h"

#include "Row.h"

std::unique_ptr<Filter> AttributeListColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return _int_view_column.createFilter(kind, relOp, value);
}

std::vector<std::string> AttributeListColumn::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds /*timezone_offset*/) const {
    return _int_view_column.getAttributes(row);
}
