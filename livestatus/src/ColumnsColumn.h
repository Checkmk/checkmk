// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ColumnsColumn_h
#define ColumnsColumn_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Column.h"
#include "StringColumn.h"
class Row;
class TableColumns;

class ColumnsColumn : public StringColumn {
public:
    enum class Type { table, name, description, type };
    ColumnsColumn(const std::string &name, const std::string &description,
                  const Column::Offsets &offsets, Type colcol,
                  const TableColumns &tablecols)
        : StringColumn(name, description, offsets)
        , _colcol(colcol)
        , _table_columns(tablecols) {}
    [[nodiscard]] std::string getValue(Row row) const override;

private:
    const Type _colcol;
    const TableColumns &_table_columns;
};

#endif  // ColumnsColumn_h
