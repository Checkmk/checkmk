// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableColumns.h"

#include <map>
#include <memory>

#include "Column.h"
#include "ColumnsColumn.h"
#include "Query.h"
#include "Row.h"

TableColumns::TableColumns(MonitoringCore *mc) : Table(mc) {
    addColumn(std::make_unique<ColumnsColumn>(
        "table", "The name of the table", Column::Offsets{},
        ColumnsColumn::Type::table, *this));
    addColumn(std::make_unique<ColumnsColumn>(
        "name", "The name of the column within the table", Column::Offsets{},
        ColumnsColumn::Type::name, *this));
    addColumn(std::make_unique<ColumnsColumn>(
        "description", "A description of the column", Column::Offsets{},
        ColumnsColumn::Type::description, *this));
    addColumn(std::make_unique<ColumnsColumn>(
        "type", "The data type of the column (int, float, string, list)",
        Column::Offsets{}, ColumnsColumn::Type::type, *this));
}

std::string TableColumns::name() const { return "columns"; }

std::string TableColumns::namePrefix() const { return "column_"; }

void TableColumns::addTable(const Table &table) { _tables.push_back(&table); }

void TableColumns::answerQuery(Query *query) {
    for (const auto *const table : _tables) {
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
    for (const auto *const table : _tables) {
        if (table->any_column(
                [&](const auto &c) { return c.get() == column; })) {
            return table->name();
        }
    }
    return "";  // never reached if no bug
}
