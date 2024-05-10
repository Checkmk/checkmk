// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableEventConsoleEvents.h"

#include <memory>

#include "livestatus/Column.h"
#include "livestatus/IntColumn.h"
#include "livestatus/ListColumn.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/Table.h"
#include "livestatus/TableHosts.h"
#include "livestatus/TimeColumn.h"
class IHost;

TableEventConsoleEvents::TableEventConsoleEvents(ICore *mc) {
    addColumns(this, *mc);
}

// static
void TableEventConsoleEvents::addColumns(Table *table, const ICore &core) {
    const ColumnOffsets offsets{};
    table->addColumn(ECRow::makeIntColumn(
        "event_id", "The unique ID for this event", offsets));
    table->addColumn(ECRow::makeIntColumn(
        "event_count", "The number of occurrences of this event within period",
        offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_text", "The textual description of the event", offsets));
    table->addColumn(ECRow::makeTimeColumn(
        "event_first",
        "Time of the first occurrence of the event (Unix timestamp)", offsets));
    table->addColumn(ECRow::makeTimeColumn(
        "event_last",
        "Time of the last occurrence of this event (Unix timestamp)", offsets));
    table->addColumn(
        ECRow::makeStringColumn("event_comment", "Event comment", offsets));
    table->addColumn(ECRow::makeIntColumn(
        "event_sl", "The service level for this event", offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_host", "The host name for this event, potentially rewritten",
        offsets));
    table->addColumn(ECRow::makeStringColumn("event_contact",
                                             "Contact information", offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_application", "Syslog tag/application", offsets));
    table->addColumn(ECRow::makeIntColumn(
        "event_pid", "The process ID of the originating process", offsets));
    table->addColumn(
        ECRow::makeIntColumn("event_priority", "Syslog priority", offsets));
    table->addColumn(
        ECRow::makeIntColumn("event_facility", "Syslog facility", offsets));
    table->addColumn(ECRow::makeStringColumn("event_rule_id",
                                             "The ID of the rule", offsets));
    table->addColumn(ECRow::makeIntColumn(
        "event_state", "The state of the event (0/1/2/3)", offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_phase",
        "The phase the event is currently in (one of open/closed/delayed/counting/ack)",
        offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_owner", "The owner of the event", offsets));
    table->addColumn(ECRow::makeListColumn(
        "event_match_groups", "Text groups from regular expression match",
        offsets));
    table->addColumn(ECRow::makeListColumn("event_contact_groups",
                                           "Contact groups", offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_ipaddress", "The IP address where the event originated",
        offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_orig_host", "The original host name for this event", offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_contact_groups_precedence",
        "Whether or not the host- or rule groups have precedence", offsets));
    table->addColumn(ECRow::makeStringColumn(
        "event_core_host",
        "The canonical name of the host for this event as known in the monitoring",
        offsets));
    table->addColumn(ECRow::makeIntColumn(
        "event_host_in_downtime",
        "Whether or not the host (if found in core) was in downtime during event creation (0/1)",
        offsets));
    table->addColumn(
        ECRow::makeListColumn("event_match_groups_syslog_application",
                              "The syslog application match groups", offsets));

    TableHosts::addColumns(table, core, "host_", offsets.add([](Row r) {
        return r.rawData<ECRow>()->host();
    }),
                           LockComments::yes, LockDowntimes::yes);
}

std::string TableEventConsoleEvents::name() const {
    return "eventconsoleevents";
}

std::string TableEventConsoleEvents::namePrefix() const {
    return "eventconsoleevents_";
}
