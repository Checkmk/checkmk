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

#include "TableEventConsoleEvents.h"
#include <memory>
#include "Column.h"
#include "Row.h"
#include "Table.h"
#include "TableHosts.h"

using std::make_unique;
using std::string;

TableEventConsoleEvents::TableEventConsoleEvents(MonitoringCore *mc)
    : TableEventConsole(mc) {
    addColumns(this, mc);
}

// static
void TableEventConsoleEvents::addColumns(Table *table, MonitoringCore *mc) {
    table->addColumn(make_unique<IntEventConsoleColumn>(
        "event_id", "The unique ID for this event"));
    table->addColumn(make_unique<IntEventConsoleColumn>(
        "event_count",
        "The number of occurrences of this event within period"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_text", "The textual description of the event"));
    table->addColumn(make_unique<TimeEventConsoleColumn>(
        "event_first",
        "Time of the first occurrence of the event (Unix timestamp)"));
    table->addColumn(make_unique<TimeEventConsoleColumn>(
        "event_last",
        "Time of the last occurrence of this event (Unix timestamp)"));
    table->addColumn(make_unique<StringEventConsoleColumn>("event_comment",
                                                           "Event comment"));
    table->addColumn(make_unique<IntEventConsoleColumn>(
        "event_sl", "The service level for this event"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_host", "Host name for this event"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_contact", "Contact information"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_application", "Syslog tag/application"));
    table->addColumn(make_unique<IntEventConsoleColumn>(
        "event_pid", "The process ID of the originating process"));
    table->addColumn(make_unique<IntEventConsoleColumn>("event_priority",
                                                        "Syslog priority"));
    table->addColumn(make_unique<IntEventConsoleColumn>("event_facility",
                                                        "Syslog facility"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_rule_id", "The ID of the rule"));
    table->addColumn(make_unique<IntEventConsoleColumn>(
        "event_state", "The state of the event (0/1/2/3)"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_phase",
        "The phase the event is currently in (one of open/closed/delayed/counting/ack)"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_owner", "The owner of the event"));
    table->addColumn(make_unique<ListEventConsoleColumn>(
        "event_match_groups", "Text groups from regular expression match"));
    table->addColumn(make_unique<ListEventConsoleColumn>("event_contact_groups",
                                                         "Contact groups"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_contact_groups_precedence",
        "Whether or not the host- or rule groups have precedence"));
    table->addColumn(make_unique<StringEventConsoleColumn>(
        "event_ipaddress", "The IP address where the event originated"));
    table->addColumn(make_unique<IntEventConsoleColumn>(
        "event_host_in_downtime",
        "Whether or not the host (if found in core) was in downtime during event creation (0/1)"));

    TableHosts::addColumns(table, mc, "host_", DANGEROUS_OFFSETOF(ECRow, _host),
                           -1);
}

string TableEventConsoleEvents::name() const { return "eventconsoleevents"; }

string TableEventConsoleEvents::namePrefix() const {
    return "eventconsoleevents_";
}

bool TableEventConsoleEvents::isAuthorized(Row row, const contact *ctc) const {
    return isAuthorizedForEvent(row, ctc);
}
