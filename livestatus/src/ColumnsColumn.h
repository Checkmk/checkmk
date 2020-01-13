// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

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
