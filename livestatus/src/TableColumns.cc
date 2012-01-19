// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

#include "TableColumns.h"
#include "ColumnsColumn.h"
#include "Query.h"

TableColumns::TableColumns()
{
    addColumn(new ColumnsColumn("table", 
                "The name of the table",       COLCOL_TABLE, this));
    addColumn(new ColumnsColumn("name", 
                "The name of the column within the table",        COLCOL_NAME,  this));
    addColumn(new ColumnsColumn("description", 
                "A description of the column", COLCOL_DESCR, this));
    addColumn(new ColumnsColumn("type", 
                "The data type of the column (int, float, string, list)",        COLCOL_TYPE,  this));
}

void TableColumns::addTable(Table *table)
{
    _tables.push_back(table);
}

void TableColumns::answerQuery(Query *query)
{
    for (_tables_t::iterator it = _tables.begin();
            it != _tables.end();
            ++it)
    { 
        Table *table = *it;
        Table::_columns_t *columns = table->columns();
        for (Table::_columns_t::iterator it = columns->begin();
                it != columns->end();
                ++it)
        {
            if (!query->processDataset(it->second)) break;
        }
    }
}

const char *TableColumns::getValue(Column *column, int colcol)
{
    static const char *typenames[6] = { "int", "float", "string", "list", "time", "dict" };

    switch (colcol)
    {
        case COLCOL_TABLE:
            return tableNameOf(column);
        case COLCOL_NAME:
            return column->name();
        case COLCOL_DESCR:
            return column->description();
        case COLCOL_TYPE:
            int type = column->type();
            return typenames[type];
    }
    return "";
}

const char *TableColumns::tableNameOf(Column *column)
{
    for (_tables_t::iterator it = _tables.begin();
            it != _tables.end();
            ++it)
    {
        Table *table = *it;
        if (table->hasColumn(column)) {
            return table->name();
        }
    }
    return ""; // never reached if no bug
}

