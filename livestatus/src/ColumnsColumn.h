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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef ColumnsColumn_h
#define ColumnsColumn_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "StringColumn.h"
class TableColumns;

#define COLCOL_TABLE 1
#define COLCOL_NAME 2
#define COLCOL_DESCR 3
#define COLCOL_TYPE 4

class ColumnsColumn : public StringColumn {
    int _colcol;
    TableColumns *_table_columns;

public:
    ColumnsColumn(std::string name, std::string description, int colcol,
                  TableColumns *tablecols, int indirect_offset = -1,
                  int extra_offset = -1)
        : StringColumn(name, description, indirect_offset, extra_offset)
        , _colcol(colcol)
        , _table_columns(tablecols) {}
    const char *getValue(void *data) override;
};

#endif  // ColumnsColumn_h
