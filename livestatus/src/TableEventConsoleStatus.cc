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

using std::string;

#ifdef CMC
TableEventConsoleStatus::TableEventConsoleStatus(Core *core)
    : TableEventConsole(core)
#else
TableEventConsoleStatus::TableEventConsoleStatus()
#endif
{
    addColumn(
        new IntEventConsoleColumn("status_messages", "The number of messages"));
    addColumn(new DoubleEventConsoleColumn("status_message_rate",
                                           "The message rate"));
    addColumn(new DoubleEventConsoleColumn("status_average_message_rate",
                                           "The average message rate"));
    addColumn(
        new IntEventConsoleColumn("status_connects", "The number of connects"));
    addColumn(new DoubleEventConsoleColumn("status_connect_rate",
                                           "The connect rate"));
    addColumn(new DoubleEventConsoleColumn("status_average_connect_rate",
                                           "The average connect rate"));
    addColumn(new IntEventConsoleColumn("status_rule_tries",
                                        "The number of rule tries"));
    addColumn(new DoubleEventConsoleColumn("status_rule_trie_rate",
                                           "The rule trie rate"));
    addColumn(new DoubleEventConsoleColumn("status_average_rule_trie_rate",
                                           "The average rule trie rate"));
    addColumn(new IntEventConsoleColumn("status_drops", "The number of drops"));
    addColumn(
        new DoubleEventConsoleColumn("status_drop_rate", "The drop rate"));
    addColumn(new DoubleEventConsoleColumn("status_average_drop_rate",
                                           "The average drop rate"));
    addColumn(
        new IntEventConsoleColumn("status_events", "The number of events"));
    addColumn(
        new DoubleEventConsoleColumn("status_event_rate", "The event rate"));
    addColumn(new DoubleEventConsoleColumn("status_average_event_rate",
                                           "The average event rate"));
    addColumn(new IntEventConsoleColumn("status_rule_hits",
                                        "The number of rule hits"));
    addColumn(new DoubleEventConsoleColumn("status_rule_hit_rate",
                                           "The rule hit rate"));
    addColumn(new DoubleEventConsoleColumn("status_average_rule_hit_rate",
                                           "The average rule hit rate"));
    addColumn(new DoubleEventConsoleColumn("status_average_processing_time",
                                           "The average processing time"));
    addColumn(new DoubleEventConsoleColumn("status_average_request_time",
                                           "The average request time"));
    addColumn(new DoubleEventConsoleColumn("status_average_sync_time",
                                           "The average sync time"));
    addColumn(new StringEventConsoleColumn(
        "status_replication_slavemode",
        "The replication slavemode (empty or one of sync/takeover)"));
    addColumn(new TimeEventConsoleColumn(
        "status_replication_last_sync",
        "Time of the last replication (Unix timestamp)"));
    addColumn(
        new IntEventConsoleColumn("status_replication_success",
                                  "Whether the replication succeeded (0/1)"));
}

string TableEventConsoleStatus::name() const { return "eventconsolestatus"; }

string TableEventConsoleStatus::namePrefix() const {
    return "eventconsolestatus_";
}
