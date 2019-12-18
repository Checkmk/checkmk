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
#include <utility>
#include <vector>
#include "Column.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "StringLambdaColumn.h"

TableCommands::TableCommands(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "");
}

std::string TableCommands::name() const { return "commands"; }

std::string TableCommands::namePrefix() const { return "command_"; }

namespace {
class CommandRow : public TableCommands::IRow {
public:
    explicit CommandRow(Command cmd) : cmd_{std::move(cmd)} {};
    [[nodiscard]] Command getCommand() const override { return cmd_; }

private:
    Command cmd_;
};
}  // namespace

// static
void TableCommands::addColumns(Table *table, const std::string &prefix) {
    table->addColumn(std::make_unique<StringLambdaColumn>(
        prefix + "name", "The name of the command", [](Row row) {
            auto r = row.rawData<Table::IRow>();
            return dynamic_cast<const IRow *>(r)->getCommand()._name;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn>(
        prefix + "line", "The shell command line", [](Row row) {
            auto r = row.rawData<Table::IRow>();
            return dynamic_cast<const IRow *>(r)->getCommand()._command_line;
        }));
}

void TableCommands::answerQuery(Query *query) {
    for (auto &cmd : core()->commands()) {
        auto r = CommandRow{cmd};
        if (!query->processDataset(Row{dynamic_cast<Table::IRow *>(&r)})) {
            break;
        }
    }
}
