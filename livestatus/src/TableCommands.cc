// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
