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

// IWYU pragma: no_include "cmc.h"
// IWYU pragma: no_include "nagios.h"
#include "Table.h"
#include <cassert>
#include <ostream>
#include "Column.h"
#include "DynamicColumn.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "StringUtils.h"

using mk::starts_with;
using std::move;
using std::string;
using std::shared_ptr;
using std::unique_ptr;

Table::Table(MonitoringCore *mc) : _mc(mc) {}

Table::~Table() = default;

void Table::addColumn(unique_ptr<Column> col) {
    string name = col->name();
    assert(column(name) == nullptr);
    _columns.emplace(name, move(col));
}

void Table::addDynamicColumn(unique_ptr<DynamicColumn> dyncol) {
    string name = dyncol->name();
    _dynamic_columns.emplace(name, move(dyncol));
}

shared_ptr<Column> Table::column(string colname) {
    // Strip away a sequence of prefixes.
    while (starts_with(colname, namePrefix())) {
        colname = colname.substr(namePrefix().size());
    }

    auto sep = colname.find(':');
    if (sep != string::npos) {
        // TODO(sp) Use shared_ptr
        return dynamicColumn(colname.substr(0, sep), colname.substr(sep + 1));
    }

    // First try exact match...
    auto it = _columns.find(colname);
    if (it != _columns.end()) {
        return it->second;
    }

    // ... then try to match with the prefix.
    it = _columns.find(namePrefix() + colname);
    if (it != _columns.end()) {
        return it->second;
    }

    // No luck.
    return nullptr;
}

unique_ptr<Column> Table::dynamicColumn(const string &name,
                                        const string &rest) {
    auto it = _dynamic_columns.find(name);
    if (it == _dynamic_columns.end()) {
        Warning(logger()) << "Unknown dynamic column '" << name << "'";
        return nullptr;
    }

    auto sep_pos = rest.find(':');
    if (sep_pos == string::npos) {
        Warning(logger()) << "Missing separator in dynamic column '" << name
                          << "'";
        return nullptr;
    }

    string name2 = rest.substr(0, sep_pos);
    if (name2.empty()) {
        Warning(logger()) << "Empty column name for dynamic column '" << name
                          << "'";
        return nullptr;
    }

    return it->second->createColumn(name2, rest.substr(sep_pos + 1));
}

bool Table::isAuthorized(Row /*unused*/, contact * /*unused*/) { return true; }

Row Table::findObject(const string & /*unused*/) { return Row(nullptr); }

Logger *Table::logger() const { return _mc->loggerLivestatus(); }
