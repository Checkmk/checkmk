// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OffsetStringColumn.h"
#include "Row.h"

std::string OffsetStringColumn::getValue(Row row) const {
    if (auto p = columnData<char *>(row)) {
        return *p == nullptr ? "" : *p;
    }
    return "";
}
