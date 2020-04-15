// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ColumnsColumn.h"
#include "Row.h"
#include "TableColumns.h"

std::string ColumnsColumn::getValue(Row row) const {
    if (auto p = columnData<Column>(row)) {
        return _table_columns.getValue(p, _colcol);
    }
    return "";
}
