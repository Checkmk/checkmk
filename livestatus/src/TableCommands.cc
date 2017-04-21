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

#include "TableCommands.h"
#include <memory>
#include "Column.h"
#include "MonitoringCore.h"
#include "OffsetSStringColumn.h"
#include "Query.h"
#include "Row.h"

using std::make_unique;
using std::string;

TableCommands::TableCommands(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", 0);
}

string TableCommands::name() const { return "commands"; }

string TableCommands::namePrefix() const { return "command_"; }

// static
void TableCommands::addColumns(Table *table, const string &prefix, int offset) {
    table->addColumn(make_unique<OffsetSStringColumn>(
        prefix + "name", "The name of the command",
        offset + DANGEROUS_OFFSETOF(Command, _name), -1, -1, -1));
    table->addColumn(make_unique<OffsetSStringColumn>(
        prefix + "line", "The shell command line",
        offset + DANGEROUS_OFFSETOF(Command, _command_line), -1, -1, -1));
}

void TableCommands::answerQuery(Query *query) {
    for (auto &cmd : core()->commands()) {
        if (!query->processDataset(Row(&cmd))) {
            break;
        }
    }
}
