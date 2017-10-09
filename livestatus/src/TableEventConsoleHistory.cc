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

#include "TableEventConsoleHistory.h"
#include <memory>
#include "Column.h"
#include "Row.h"
#include "TableEventConsoleEvents.h"

TableEventConsoleHistory::TableEventConsoleHistory(MonitoringCore *mc)
    : TableEventConsole(mc) {
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "history_line", "The line number of the event in the history file"));
    addColumn(std::make_unique<TimeEventConsoleColumn>(
        "history_time",
        "Time when the event was written into the history file (Unix timestamp)"));
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "history_what",
        "What happened (one of ARCHIVED/AUTODELETE/CANCELLED/CHANGESTATE/COUNTFAILED/COUNTREACHED/DELAYOVER/DELETE/EMAIL/EXPIRED/NEW/NOCOUNT/ORPHANED/SCRIPT/UPDATE)"));
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "history_who", "The user who triggered the command"));
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "history_addinfo",
        "Additional information, like email recipient/subject or action ID"));
    TableEventConsoleEvents::addColumns(this, mc);
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
