// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "AttributeListAsIntColumn.h"

#include "AttributeListColumnUtils.h"
#include "IntFilter.h"
#include "Row.h"

std::unique_ptr<Filter> AttributeListAsIntColumn::createFilter(
    Filter::Kind kind, RelationalOperator relOp,
    const std::string &value) const {
    return std::make_unique<IntFilter>(
        kind, name(),
        [this](Row row, const contact *auth_user) {
            return this->getValue(row, auth_user);
        },
        relOp, column::attribute_list::refValueFor(value, logger()));
}

int32_t AttributeListAsIntColumn::getValue(
    Row row, const contact * /*auth_user*/) const {
    if (const auto *p = columnData<unsigned long>(row)) {
        return static_cast<int32_t>(*p);
    }
    return 0;
}
