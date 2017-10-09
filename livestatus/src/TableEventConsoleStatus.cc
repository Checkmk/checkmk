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
        "The time when the Event Console config was loaded"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_num_open_events", "The number of currently open events"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_virtual_memory_size",
        "The current virtual memory size in bytes"));

    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_messages",
        "The number of messages received since startup of the Event Console"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_message_rate", "The incoming message rate"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_message_rate", "The average incoming message rate"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_connects", "The number of connects"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>("status_connect_rate",
                                                         "The connect rate"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_connect_rate", "The average connect rate"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_rule_tries", "The number of rule tries"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_rule_trie_rate", "The rule trie rate"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_rule_trie_rate", "The average rule trie rate"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_drops",
        "The number of message drops (decided by a rule) since startup of the Event Console"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>("status_drop_rate",
                                                         "The drop rate"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_drop_rate", "The average drop rate"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_overflows",
        "The number of message overflows, i.e. messages simply dropped due to an overflow of the Event Console"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>("status_overflow_rate",
                                                         "The overflow rate"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_overflow_rate", "The average overflow rate"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_events",
        "The number of events received since startup of the Event Console"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>("status_event_rate",
                                                         "The event rate"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_event_rate", "The average event rate"));

    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_rule_hits",
        "The number of rule hits since startup of the Event Console"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>("status_rule_hit_rate",
                                                         "The rule hit rate"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_rule_hit_rate", "The average rule hit rate"));

    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_processing_time",
        "The average incoming message processing time"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_request_time",
        "The average status client request time"));
    addColumn(std::make_unique<DoubleEventConsoleColumn>(
        "status_average_sync_time", "The average sync time"));
    addColumn(std::make_unique<StringEventConsoleColumn>(
        "status_replication_slavemode",
        "The replication slavemode (empty or one of sync/takeover)"));
    addColumn(std::make_unique<TimeEventConsoleColumn>(
        "status_replication_last_sync",
        "Time of the last replication (Unix timestamp)"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_replication_success",
        "Whether the replication succeeded (0/1)"));

    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_event_limit_host",
        "The currently active event limit for hosts"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_event_limit_rule",
        "The currently active event limit for rules"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_event_limit_overall",
        "The currently active event limit for all events"));

    addColumn(std::make_unique<ListEventConsoleColumn>(
        "status_event_limit_active_hosts",
        "List of host names with active event limit"));
    addColumn(std::make_unique<ListEventConsoleColumn>(
        "status_event_limit_active_rules",
        "List of rule IDs which rules event limit is active"));
    addColumn(std::make_unique<IntEventConsoleColumn>(
        "status_event_limit_active_overall",
        "Whether or not the overall event limit is in effect (0/1)"));
}

std::string TableEventConsoleStatus::name() const {
    return "eventconsolestatus";
}

std::string TableEventConsoleStatus::namePrefix() const {
    return "eventconsolestatus_";
}
