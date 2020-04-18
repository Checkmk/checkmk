// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OffsetIntColumn.h"
#include "Row.h"

int32_t OffsetIntColumn::getValue(Row row,
                                  const contact* /* auth_user */) const {
    if (auto p = columnData<int>(row)) {
        return static_cast<int32_t>(*p);
    }
    return 0;
}
