// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableEventConsoleEvents.h"

#include <memory>

#include "Column.h"
#include "Row.h"
#include "Table.h"
#include "TableHosts.h"

TableEventConsoleEvents::TableEventConsoleEvents(MonitoringCore *mc)
    : TableEventConsole(mc) {
    addColumns(this);
}

// static
void TableEventConsoleEvents::addColumns(Table *table) {
    table->addColumn(std::make_unique<IntEventConsoleColumn>(
        "event_id", "The unique ID for this event", Column::Offsets{}));
    table->addColumn(std::make_unique<IntEventConsoleColumn>(
        "event_count", "The number of occurrences of this event within period",
        Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_text", "The textual description of the event",
        Column::Offsets{}));
    table->addColumn(std::make_unique<TimeEventConsoleColumn>(
        "event_first",
        "Time of the first occurrence of the event (Unix timestamp)",
        Column::Offsets{}));
    table->addColumn(std::make_unique<TimeEventConsoleColumn>(
        "event_last",
        "Time of the last occurrence of this event (Unix timestamp)",
        Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_comment", "Event comment", Column::Offsets{}));
    table->addColumn(std::make_unique<IntEventConsoleColumn>(
        "event_sl", "The service level for this event", Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_host", "Host name for this event", Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_contact", "Contact information", Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_application", "Syslog tag/application", Column::Offsets{}));
    table->addColumn(std::make_unique<IntEventConsoleColumn>(
        "event_pid", "The process ID of the originating process",
        Column::Offsets{}));
    table->addColumn(std::make_unique<IntEventConsoleColumn>(
        "event_priority", "Syslog priority", Column::Offsets{}));
    table->addColumn(std::make_unique<IntEventConsoleColumn>(
        "event_facility", "Syslog facility", Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_rule_id", "The ID of the rule", Column::Offsets{}));
    table->addColumn(std::make_unique<IntEventConsoleColumn>(
        "event_state", "The state of the event (0/1/2/3)", Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_phase",
        "The phase the event is currently in (one of open/closed/delayed/counting/ack)",
        Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_owner", "The owner of the event", Column::Offsets{}));
    table->addColumn(std::make_unique<ListEventConsoleColumn>(
        "event_match_groups", "Text groups from regular expression match",
        Column::Offsets{}));
    table->addColumn(std::make_unique<ListEventConsoleColumn>(
        "event_contact_groups", "Contact groups", Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_contact_groups_precedence",
        "Whether or not the host- or rule groups have precedence",
        Column::Offsets{}));
    table->addColumn(std::make_unique<StringEventConsoleColumn>(
        "event_ipaddress", "The IP address where the event originated",
        Column::Offsets{}));
    table->addColumn(std::make_unique<IntEventConsoleColumn>(
        "event_host_in_downtime",
        "Whether or not the host (if found in core) was in downtime during event creation (0/1)",
        Column::Offsets{}));

    TableHosts::addColumns(table, "host_", DANGEROUS_OFFSETOF(ECRow, _host),
                           -1);
}

std::string TableEventConsoleEvents::name() const {
    return "eventconsoleevents";
}

std::string TableEventConsoleEvents::namePrefix() const {
    return "eventconsoleevents_";
}

bool TableEventConsoleEvents::isAuthorized(Row row, const contact *ctc) const {
    return isAuthorizedForEvent(row, ctc);
}
