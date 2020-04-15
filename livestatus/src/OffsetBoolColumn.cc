// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OffsetBoolColumn.h"
#include "Row.h"

int32_t OffsetBoolColumn::getValue(Row row,
                                   const contact* /* auth_user */) const {
    if (auto p = columnData<bool>(row)) {
        return *p ? 1 : 0;
    }
    return 0;
}
