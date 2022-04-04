// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableEventConsoleStatus.h"

#include <functional>
#include <memory>
#include <vector>

#include "Column.h"
#include "DoubleColumn.h"
#include "IntColumn.h"
#include "ListColumn.h"
#include "StringColumn.h"
#include "TimeColumn.h"
class User;

TableEventConsoleStatus::TableEventConsoleStatus(MonitoringCore *mc)
    : TableEventConsole{mc, [](const User & /*user*/, const ECRow & /*row*/) {
                            return true;
                        }} {
    ColumnOffsets offsets{};
    addColumn(ECRow::makeIntColumn(
        "status_config_load_time",
        "The time when the Event Console config was loaded", offsets));
    addColumn(ECRow::makeIntColumn("status_num_open_events",
                                   "The number of currently open events",
                                   offsets));
    addColumn(ECRow::makeIntColumn("status_virtual_memory_size",
                                   "The current virtual memory size in bytes",
                                   offsets));

    addColumn(ECRow::makeIntColumn(
        "status_messages",
        "The number of messages received since startup of the Event Console",
        offsets));
    addColumn(ECRow::makeDoubleColumn("status_message_rate",
                                      "The incoming message rate", offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_message_rate",
                                      "The average incoming message rate",
                                      offsets));
    addColumn(ECRow::makeIntColumn("status_connects", "The number of connects",
                                   offsets));
    addColumn(ECRow::makeDoubleColumn("status_connect_rate", "The connect rate",
                                      offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_connect_rate",
                                      "The average connect rate", offsets));
    addColumn(ECRow::makeIntColumn("status_rule_tries",
                                   "The number of rule tries", offsets));
    addColumn(ECRow::makeDoubleColumn("status_rule_trie_rate",
                                      "The rule trie rate", offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_rule_trie_rate",
                                      "The average rule trie rate", offsets));
    addColumn(ECRow::makeIntColumn(
        "status_drops",
        "The number of message drops (decided by a rule) since startup of the Event Console",
        offsets));
    addColumn(
        ECRow::makeDoubleColumn("status_drop_rate", "The drop rate", offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_drop_rate",
                                      "The average drop rate", offsets));
    addColumn(ECRow::makeIntColumn(
        "status_overflows",
        "The number of message overflows, i.e. messages simply dropped due to an overflow of the Event Console",
        offsets));
    addColumn(ECRow::makeDoubleColumn("status_overflow_rate",
                                      "The overflow rate", offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_overflow_rate",
                                      "The average overflow rate", offsets));
    addColumn(ECRow::makeIntColumn(
        "status_events",
        "The number of events received since startup of the Event Console",
        offsets));
    addColumn(ECRow::makeDoubleColumn("status_event_rate", "The event rate",
                                      offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_event_rate",
                                      "The average event rate", offsets));

    addColumn(ECRow::makeIntColumn(
        "status_rule_hits",
        "The number of rule hits since startup of the Event Console", offsets));
    addColumn(ECRow::makeDoubleColumn("status_rule_hit_rate",
                                      "The rule hit rate", offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_rule_hit_rate",
                                      "The average rule hit rate", offsets));

    addColumn(ECRow::makeDoubleColumn(
        "status_average_processing_time",
        "The average incoming message processing time", offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_request_time",
                                      "The average status client request time",
                                      offsets));
    addColumn(ECRow::makeDoubleColumn("status_average_sync_time",
                                      "The average sync time", offsets));
    addColumn(ECRow::makeStringColumn(
        "status_replication_slavemode",
        "The replication slavemode (empty or one of sync/takeover)", offsets));
    addColumn(ECRow::makeTimeColumn(
        "status_replication_last_sync",
        "Time of the last replication (Unix timestamp)", offsets));
    addColumn(ECRow::makeIntColumn("status_replication_success",
                                   "Whether the replication succeeded (0/1)",
                                   offsets));

    addColumn(ECRow::makeIntColumn("status_event_limit_host",
                                   "The currently active event limit for hosts",
                                   offsets));
    addColumn(ECRow::makeIntColumn("status_event_limit_rule",
                                   "The currently active event limit for rules",
                                   offsets));
    addColumn(ECRow::makeIntColumn(
        "status_event_limit_overall",
        "The currently active event limit for all events", offsets));

    addColumn(ECRow::makeListColumn(
        "status_event_limit_active_hosts",
        "List of host names with active event limit", offsets));
    addColumn(ECRow::makeListColumn(
        "status_event_limit_active_rules",
        "List of rule IDs which rules event limit is active", offsets));
    addColumn(ECRow::makeIntColumn(
        "status_event_limit_active_overall",
        "Whether or not the overall event limit is in effect (0/1)", offsets));
}

std::string TableEventConsoleStatus::name() const {
    return "eventconsolestatus";
}

std::string TableEventConsoleStatus::namePrefix() const {
    return "eventconsolestatus_";
}

Row TableEventConsoleStatus::getDefault() const { return Row{this}; }
