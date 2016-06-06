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
#include <ostream>
#include "Column.h"
#include "DynamicColumn.h"
#include "Logger.h"

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

    const char *sep_pos = strchr(colname, ':');
    if (sep_pos != nullptr) {
        return dynamicColumn(string(colname, sep_pos), string(sep_pos + 1));
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

Column *Table::dynamicColumn(const string &name, const string &rest) {
    auto it = _dynamic_columns.find(name);
    if (it == _dynamic_columns.end()) {
        Warning() << "Unknown dynamic column '" << name << "'";
        return nullptr;
    }

    auto sep_pos = rest.find(':');
    if (sep_pos == string::npos) {
        Warning() << "Missing separator in dynamic column '" << name << "'";
        return nullptr;
    }

    string name2 = rest.substr(0, sep_pos);
    if (name2.empty()) {
        Warning() << "Empty column name for dynamic column '" << name << "'";
        return nullptr;
    }

    return it->second->createColumn(name2, rest.substr(sep_pos + 1));
}

bool Table::isAuthorized(contact * /*unused*/, void * /*unused*/) {
    return true;
}

void *Table::findObject(char * /*unused*/) { return nullptr; }
