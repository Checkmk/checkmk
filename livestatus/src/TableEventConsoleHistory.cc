// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableEventConsoleHistory.h"
#include <memory>
#include "Column.h"
#include "Row.h"
#include "TableEventConsoleEvents.h"

TableEventConsoleHistory::TableEventConsoleHistory(MonitoringCore *mc)
    : TableEventConsole(mc) {
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "history_line", "The line number of the event in the history file",
        Column::Offsets{}));
    addColumn(std::make_unique<TimeEventConsoleColumn>(
        "history_time",
        "Time when the event was written into the history file (Unix timestamp)",
        Column::Offsets{}));
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "history_what",
        "What happened (one of ARCHIVED/AUTODELETE/CANCELLED/CHANGESTATE/COUNTFAILED/COUNTREACHED/DELAYOVER/DELETE/EMAIL/EXPIRED/NEW/NOCOUNT/ORPHANED/SCRIPT/UPDATE)",
        Column::Offsets{}));
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "history_who", "The user who triggered the command",
        Column::Offsets{}));
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "history_addinfo",
        "Additional information, like email recipient/subject or action ID",
        Column::Offsets{}));
    TableEventConsoleEvents::addColumns(this);
}

std::string TableEventConsoleHistory::name() const {
    return "eventconsolehistory";
}

std::string TableEventConsoleHistory::namePrefix() const {
    return "eventconsolehistory_";
}

bool TableEventConsoleHistory::isAuthorized(Row row, const contact *ctc) const {
    return isAuthorizedForEvent(row, ctc);
}
