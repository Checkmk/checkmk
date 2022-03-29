// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableColumns.h"

#include <map>
#include <memory>

#include "Column.h"
#include "Query.h"
#include "Row.h"
#include "StringColumn.h"

TableColumns::TableColumns(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<Column>>(
        "table", "The name of the table", offsets, [this](const Column &col) {
            return this->getValue(col, Type::table);
        }));
    addColumn(std::make_unique<StringColumn<Column>>(
        "name", "The name of the column within the table", offsets,
        [this](const Column &col) { return this->getValue(col, Type::name); }));
    addColumn(std::make_unique<StringColumn<Column>>(
        "description", "A description of the column", offsets,
        [this](const Column &col) {
            return this->getValue(col, Type::description);
        }));
    addColumn(std::make_unique<StringColumn<Column>>(
        "type", "The data type of the column (int, float, string, list)",
        offsets,
        [this](const Column &col) { return this->getValue(col, Type::type); }));
}

std::string TableColumns::name() const { return "columns"; }

std::string TableColumns::namePrefix() const { return "column_"; }

void TableColumns::addTable(const Table &table) { _tables.push_back(&table); }

void TableColumns::answerQuery(Query &query, const User & /*user*/) {
    for (const auto *const table : _tables) {
        table->any_column(
            [&](const auto &c) { return !query.processDataset(Row{c.get()}); });
    }
}

std::string TableColumns::getValue(const Column &column, Type colcol) const {
    static const char *typenames[8] = {"int",  "float", "string", "list",
                                       "time", "dict",  "blob",   "null"};

    switch (colcol) {
        case Type::table:
            return tableNameOf(column);
        case Type::name:
            return column.name();
        case Type::description:
            return column.description();
        case Type::type:
            return typenames[static_cast<int>(column.type())];
    }
    return "";
}

std::string TableColumns::tableNameOf(const Column &column) const {
    for (const auto *const table : _tables) {
        if (table->any_column(
                [&](const auto &c) { return c.get() == &column; })) {
            return table->name();
        }
    }
    return "";  // never reached if no bug
}
