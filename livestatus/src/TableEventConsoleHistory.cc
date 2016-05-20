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

#include "TableEventConsoleHistory.h"

TableEventConsoleHistory::TableEventConsoleHistory() {
    addColumn(new StringEventConsoleColumn("history_line", "blah"));
    addColumn(new StringEventConsoleColumn("history_time", "blah"));
    addColumn(new StringEventConsoleColumn("history_what", "blah"));
    addColumn(new StringEventConsoleColumn("history_who", "blah"));
    addColumn(new StringEventConsoleColumn("history_addinfo", "blah"));
    addColumn(new StringEventConsoleColumn("event_id", "blah"));
    addColumn(new StringEventConsoleColumn("event_count", "blah"));
    addColumn(new StringEventConsoleColumn("event_text", "blah"));
    addColumn(new StringEventConsoleColumn("event_first", "blah"));
    addColumn(new StringEventConsoleColumn("event_last", "blah"));
    addColumn(new StringEventConsoleColumn("event_comment", "blah"));
    addColumn(new StringEventConsoleColumn("event_sl", "blah"));
    addColumn(new StringEventConsoleColumn("event_host", "blah"));
    addColumn(new StringEventConsoleColumn("event_contact", "blah"));
    addColumn(new StringEventConsoleColumn("event_application", "blah"));
    addColumn(new StringEventConsoleColumn("event_pid", "blah"));
    addColumn(new StringEventConsoleColumn("event_priority", "blah"));
    addColumn(new StringEventConsoleColumn("event_facility", "blah"));
    addColumn(new StringEventConsoleColumn("event_rule_id", "blah"));
    addColumn(new StringEventConsoleColumn("event_state", "blah"));
    addColumn(new StringEventConsoleColumn("event_phase", "blah"));
    addColumn(new StringEventConsoleColumn("event_owner", "blah"));
    addColumn(new StringEventConsoleColumn("event_match_groups", "blah"));
    addColumn(new StringEventConsoleColumn("event_contact_groups", "blah"));
    addColumn(new StringEventConsoleColumn("event_ipaddress", "blah"));
}

const char *TableEventConsoleHistory::name() const {
    return "eventconsolehistory";
}

const char *TableEventConsoleHistory::namePrefix() const {
    return "eventconsolehistory_";
}
