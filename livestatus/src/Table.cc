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

#include "Table.h"
#include <string.h>
#include "Column.h"
#include "DynamicColumn.h"

using std::string;

Table::Table() {}

Table::~Table() {
    for (auto &column : _columns) {
        delete column.second;
    }

    for (auto &dynamic_column : _dynamic_columns) {
        delete dynamic_column.second;
    }
}

void Table::addColumn(Column *col) {
    // Do not insert column if one with that name already exists. Delete that
    // column in that case. (Needed e.g. for TableLog->TableHosts, which both
    // define host_name.)
    if (column(col->name()) != nullptr) {
        delete col;
    } else {
        _columns.emplace(col->name(), col);
    }
}

void Table::addDynamicColumn(DynamicColumn *dyncol) {
    _dynamic_columns.emplace(dyncol->name(), dyncol);
}

Column *Table::column(const char *colname) {
    // Strip away a sequence of prefixes.
    int prefix_len = strlen(namePrefix());
    while (strncmp(colname, namePrefix(), prefix_len) == 0) {
        colname += prefix_len;
    }

    if (strchr(colname, ':') != nullptr) {
        return dynamicColumn(colname);
    }

    // First try exact match...
    auto it = _columns.find(colname);
    if (it != _columns.end()) {
        return it->second;
    }

    // ... then try to match with the prefix.
    it = _columns.find(string(namePrefix()) + colname);
    if (it != _columns.end()) {
        return it->second;
    }

    // No luck.
    return nullptr;
}

Column *Table::dynamicColumn(const char *colname_with_args) {
    const char *sep_pos = strchr(colname_with_args, ':');
    string name(colname_with_args, sep_pos - colname_with_args);

    const char *argstring = sep_pos + 1;

    auto it = _dynamic_columns.find(name);
    if (it != _dynamic_columns.end()) {
        return it->second->createColumn(argstring);
    }
    return nullptr;
}

bool Table::isAuthorized(contact * /*unused*/, void * /*unused*/) {
    return true;
}

void *Table::findObject(char * /*unused*/) { return nullptr; }
