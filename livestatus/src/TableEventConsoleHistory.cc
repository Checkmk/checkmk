// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableEventConsoleHistory.h"

#include <memory>

#include "TableEventConsoleEvents.h"
#include "livestatus/Column.h"
#include "livestatus/IntColumn.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TimeColumn.h"

TableEventConsoleHistory::TableEventConsoleHistory(MonitoringCore *mc)
    : TableEventConsole{mc} {
    const ColumnOffsets offsets{};
    addColumn(ECRow::makeIntColumn(
        "history_line", "The line number of the event in the history file",
        offsets));
    addColumn(ECRow::makeTimeColumn(
        "history_time",
        "Time when the event was written into the history file (Unix timestamp)",
        offsets));
    addColumn(ECRow::makeStringColumn(
        "history_what",
        "What happened (one of ARCHIVED/AUTODELETE/CANCELLED/CHANGESTATE/COUNTFAILED/COUNTREACHED/DELAYOVER/DELETE/EMAIL/EXPIRED/NEW/NOCOUNT/ORPHANED/SCRIPT/UPDATE)",
        offsets));
    addColumn(ECRow::makeStringColumn(
        "history_who", "The user who triggered the command", offsets));
    addColumn(ECRow::makeStringColumn(
        "history_addinfo",
        "Additional information, like email recipient/subject or action ID",
        offsets));
    TableEventConsoleEvents::addColumns(this);
}

std::string TableEventConsoleHistory::name() const {
    return "eventconsolehistory";
}

std::string TableEventConsoleHistory::namePrefix() const {
    return "eventconsolehistory_";
}
