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

#include "TableEventConsoleStatus.h"
#include <memory>
#include "Column.h"

TableEventConsoleStatus::TableEventConsoleStatus(MonitoringCore *mc)
    : TableEventConsole(mc) {
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_config_load_time",
        "The time when the Event Console config was loaded",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_num_open_events", "The number of currently open events",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_virtual_memory_size",
        "The current virtual memory size in bytes", Column::Offsets{}));

    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_messages",
        "The number of messages received since startup of the Event Console",
        Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_message_rate", "The incoming message rate", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_message_rate", "The average incoming message rate",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_connects", "The number of connects", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_connect_rate", "The connect rate", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_connect_rate", "The average connect rate",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_rule_tries", "The number of rule tries", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_rule_trie_rate", "The rule trie rate", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_rule_trie_rate", "The average rule trie rate",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_drops",
        "The number of message drops (decided by a rule) since startup of the Event Console",
        Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_drop_rate", "The drop rate", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_drop_rate", "The average drop rate",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_overflows",
        "The number of message overflows, i.e. messages simply dropped due to an overflow of the Event Console",
        Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_overflow_rate", "The overflow rate", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_overflow_rate", "The average overflow rate",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_events",
        "The number of events received since startup of the Event Console",
        Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_event_rate", "The event rate", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_event_rate", "The average event rate",
        Column::Offsets{}));

    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_rule_hits",
        "The number of rule hits since startup of the Event Console",
        Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_rule_hit_rate", "The rule hit rate", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_rule_hit_rate", "The average rule hit rate",
        Column::Offsets{}));

    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_processing_time",
        "The average incoming message processing time", Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_request_time", "The average status client request time",
        Column::Offsets{}));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_sync_time", "The average sync time",
        Column::Offsets{}));
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "status_replication_slavemode",
        "The replication slavemode (empty or one of sync/takeover)",
        Column::Offsets{}));
    addColumn(std::make_unique<TimeEventConsoleColumn>(
        "status_replication_last_sync",
        "Time of the last replication (Unix timestamp)", Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_replication_success", "Whether the replication succeeded (0/1)",
        Column::Offsets{}));

    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_event_limit_host", "The currently active event limit for hosts",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_event_limit_rule", "The currently active event limit for rules",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_event_limit_overall",
        "The currently active event limit for all events", Column::Offsets{}));

    addColumn(std::make_unique<ListEventConsoleColumn>(
        "status_event_limit_active_hosts",
        "List of host names with active event limit", Column::Offsets{}));
    addColumn(std::make_unique<ListEventConsoleColumn>(
        "status_event_limit_active_rules",
        "List of rule IDs which rules event limit is active",
        Column::Offsets{}));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_event_limit_active_overall",
        "Whether or not the overall event limit is in effect (0/1)",
        Column::Offsets{}));
}

std::string TableEventConsoleStatus::name() const {
    return "eventconsolestatus";
}

std::string TableEventConsoleStatus::namePrefix() const {
    return "eventconsolestatus_";
}
