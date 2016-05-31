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

#include "TableEventConsoleEvents.h"
#include <string>
#include "Table.h"
#include "TableHosts.h"
#ifdef CMC
#include "Core.h"
#include "World.h"
using std::recursive_mutex;
#endif

using std::string;

#ifdef CMC
TableEventConsoleEvents::TableEventConsoleEvents(
    const Notes &downtimes_holder, const Notes &comments_holder,
    std::recursive_mutex &holder_lock, Core *core)
    : TableEventConsole(core) {
    addColumns(this, downtimes_holder, comments_holder, holder_lock, core);
}
#else
TableEventConsoleEvents::TableEventConsoleEvents(
    const DowntimesOrComments &downtimes_holder,
    const DowntimesOrComments &comments_holder) {
    addColumns(this, downtimes_holder, comments_holder);
}
#endif

// static
#ifdef CMC
void TableEventConsoleEvents::addColumns(Table *table,
                                         const Notes &downtimes_holder,
                                         const Notes &comments_holder,
                                         std::recursive_mutex &holder_lock,
                                         Core *core)
#else
void TableEventConsoleEvents::addColumns(
    Table *table, const DowntimesOrComments &downtimes_holder,
    const DowntimesOrComments &comments_holder)
#endif
{
    table->addColumn(
        new IntEventConsoleColumn("event_id", "The unique ID for this event"));
    table->addColumn(new IntEventConsoleColumn(
        "event_count",
        "The number of occurrences of this event within period"));
    table->addColumn(new StringEventConsoleColumn(
        "event_text", "The textual description of the event"));
    table->addColumn(new TimeEventConsoleColumn(
        "event_first",
        "Time of the first occurrence of the event (Unix timestamp)"));
    table->addColumn(new TimeEventConsoleColumn(
        "event_last",
        "Time of the last occurrence of this event (Unix timestamp)"));
    table->addColumn(
        new StringEventConsoleColumn("event_comment", "Event comment"));
    table->addColumn(new IntEventConsoleColumn(
        "event_sl", "The service level for this event"));
    table->addColumn(
        new StringEventConsoleColumn("event_host", "Host name for this event"));
    table->addColumn(
        new StringEventConsoleColumn("event_contact", "Contact information"));
    table->addColumn(new StringEventConsoleColumn("event_application",
                                                  "Syslog tag/application"));
    table->addColumn(new IntEventConsoleColumn(
        "event_pid", "The process ID of the originating process"));
    table->addColumn(
        new IntEventConsoleColumn("event_priority", "Syslog priority"));
    table->addColumn(
        new IntEventConsoleColumn("event_facility", "Syslog facility"));
    table->addColumn(
        new StringEventConsoleColumn("event_rule_id", "The ID of the rule"));
    table->addColumn(new IntEventConsoleColumn(
        "event_state", "The state of the event (0/1/2/3)"));
    table->addColumn(
        new StringEventConsoleColumn("event_phase",
                                     "The phase the event is currently in (one "
                                     "of open/closed/delayed/counting/ack)"));
    table->addColumn(
        new StringEventConsoleColumn("event_owner", "The owner of the event"));
    table->addColumn(new ListEventConsoleColumn(
        "event_match_groups", "Text groups from regular expression match"));
    table->addColumn(
        new ListEventConsoleColumn("event_contact_groups", "Contact groups"));
    table->addColumn(new StringEventConsoleColumn(
        "event_ipaddress", "The IP address where the event originated"));

    Row row;
    TableHosts::addColumns(
        table, "host_",
        reinterpret_cast<char *>(&row._host) - reinterpret_cast<char *>(&row),
        -1, downtimes_holder, comments_holder
#ifdef CMC
        ,
        holder_lock, core
#endif
        );
}

const char *TableEventConsoleEvents::name() const {
    return "eventconsoleevents";
}

const char *TableEventConsoleEvents::namePrefix() const {
    return "eventconsoleevents_";
}
