// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableCommands.h"

#include <memory>
#include <vector>

#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"

using row_type = Command;

TableCommands::TableCommands() { addColumns(this, "", ColumnOffsets{}); }

std::string TableCommands::name() const { return "commands"; }

std::string TableCommands::namePrefix() const { return "command_"; }

// static
void TableCommands::addColumns(Table *table, const std::string &prefix,
                               const ColumnOffsets &offsets) {
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "name", "The name of the command", offsets,
        [](const row_type &row) { return row._name; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "line", "The shell command line", offsets,
        [](const row_type &row) { return row._command_line; }));
}

void TableCommands::answerQuery(Query &query, const User & /*user*/,
                                const ICore &core) {
    for (auto &cmd : core.commands()) {
        if (!query.processDataset(Row{&cmd})) {
            break;
        }
    }
}
