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

#include "TableColumns.h"
#include <map>
#include <memory>
#include "Column.h"
#include "ColumnsColumn.h"
#include "Query.h"
#include "Row.h"

TableColumns::TableColumns(MonitoringCore *mc) : Table(mc) {
    addColumn(std::make_unique<ColumnsColumn>(
        "table", "The name of the table", -1, -1, -1, 0,
        ColumnsColumn::Type::table, *this));
    addColumn(std::make_unique<ColumnsColumn>(
        "name", "The name of the column within the table", -1, -1, -1, 0,
        ColumnsColumn::Type::name, *this));
    addColumn(std::make_unique<ColumnsColumn>(
        "description", "A description of the column", -1, -1, -1, 0,
        ColumnsColumn::Type::description, *this));
    addColumn(std::make_unique<ColumnsColumn>(
        "type", "The data type of the column (int, float, string, list)", -1,
        -1, -1, 0, ColumnsColumn::Type::type, *this));
}

std::string TableColumns::name() const { return "columns"; }

std::string TableColumns::namePrefix() const { return "column_"; }

void TableColumns::addTable(const Table &table) { _tables.push_back(&table); }

void TableColumns::answerQuery(Query *query) {
    for (auto table : _tables) {
        table->any_column([&](const auto &c) {
            return !query->processDataset(Row(c.get()));
        });
    }
}

std::string TableColumns::getValue(const Column *column,
                                   ColumnsColumn::Type colcol) const {
    static const char *typenames[8] = {"int",  "float", "string", "list",
                                       "time", "dict",  "blob",   "null"};

    switch (colcol) {
        case ColumnsColumn::Type::table:
            return tableNameOf(column);
        case ColumnsColumn::Type::name:
            return column->name();
        case ColumnsColumn::Type::description:
            return column->description();
        case ColumnsColumn::Type::type:
            return typenames[static_cast<int>(column->type())];
    }
    return "";
}

std::string TableColumns::tableNameOf(const Column *column) const {
    for (auto table : _tables) {
        if (table->any_column(
                [&](const auto &c) { return c.get() == column; })) {
            return table->name();
        }
    }
    return "";  // never reached if no bug
}
