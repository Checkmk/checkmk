// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#include <cstddef>

#define NSCORE
#include "nagios.h"
#include "Query.h"
#include "OffsetStringColumn.h"
#include "TableCommands.h"



extern command *command_list;

TableCommands::TableCommands()
{
    addColumns(this, "", -1);
}


void TableCommands::addColumns(Table *table, string prefix, int indirect_offset)
{
    command cmd;
    char *ref = (char *)&cmd;
    table->addColumn(new OffsetStringColumn(prefix + "name",
                "The name of the command", (char *)(&cmd.name) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "line",
                "The shell command line", (char *)(&cmd.command_line) - ref, indirect_offset));
}


void TableCommands::answerQuery(Query *query)
{
    command *cmd = command_list;
    while (cmd) {
        if (!query->processDataset(cmd)) break;
        cmd = cmd->next;
    }
}
