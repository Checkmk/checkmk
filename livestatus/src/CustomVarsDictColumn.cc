// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "CustomVarsDictColumn.h"

#include "CustomVarsDictFilter.h"
#include "MonitoringCore.h"
#include "Row.h"

std::unique_ptr<Filter> CustomVarsDictColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<CustomVarsDictFilter>(
        kind, name(), [this](Row row) { return this->getValue(row); }, relOp,
        value);
}

DictColumn::value_type CustomVarsDictColumn::getValue(Row row) const {
    if (const auto *p = columnData<void>(row)) {
        return _mc->customAttributes(p, _kind);
    }
    return {};
}
