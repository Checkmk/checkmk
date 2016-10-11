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

#ifndef Store_h
#define Store_h

#include "config.h"  // IWYU pragma: keep
#include <list>
#include <map>
#include <mutex>
#include <string>
#include "CommandsHolderNagios.h"
#include "DowntimesOrComments.h"
#include "LogCache.h"
#include "TableColumns.h"
#include "TableCommands.h"
#include "TableComments.h"
#include "TableContactgroups.h"
#include "TableContacts.h"
#include "TableDowntimes.h"
#include "TableEventConsoleEvents.h"
#include "TableEventConsoleHistory.h"
#include "TableEventConsoleReplication.h"
#include "TableEventConsoleStatus.h"
#include "TableHostgroups.h"
#include "TableHosts.h"
#include "TableHostsByGroup.h"
#include "TableLog.h"
#include "TableServicegroups.h"
#include "TableServices.h"
#include "TableServicesByGroup.h"
#include "TableServicesByHostGroup.h"
#include "TableStateHistory.h"
#include "TableStatus.h"
#include "TableTimeperiods.h"
#include "nagios.h"
class Logger;
class InputBuffer;
class OutputBuffer;
class Table;

class Store {
public:
    explicit Store(Logger *logger);
    bool answerRequest(InputBuffer *, OutputBuffer *);

    void registerDowntime(nebstruct_downtime_data *);
    void registerComment(nebstruct_comment_data *);

private:
    CommandsHolderNagios _commands_holder;
    DowntimesOrComments _downtimes;
    DowntimesOrComments _comments;
    LogCache _log_cache;
    TableContacts _table_contacts;
    TableCommands _table_commands;
    TableHostgroups _table_hostgroups;
    TableHosts _table_hosts;
    TableHostsByGroup _table_hostsbygroup;
    TableServicegroups _table_servicegroups;
    TableServices _table_services;
    TableServicesByGroup _table_servicesbygroup;
    TableServicesByHostGroup _table_servicesbyhostgroup;
    TableTimeperiods _table_timeperiods;
    TableContactgroups _table_contactgroups;
    TableDowntimes _table_downtimes;
    TableComments _table_comments;
    TableStatus _table_status;
    TableLog _table_log;
    TableStateHistory _table_statehistory;
    TableColumns _table_columns;
    TableEventConsoleEvents _table_eventconsoleevents;
    TableEventConsoleHistory _table_eventconsolehistory;
    TableEventConsoleStatus _table_eventconsolestatus;
    TableEventConsoleReplication _table_eventconsolereplication;
    Logger *const _logger;

    std::map<std::string, Table *> _tables;

    std::mutex _command_mutex;

    void addTable(Table *table);
    Table *findTable(const std::string &name);
    void answerGetRequest(const std::list<std::string> &lines, OutputBuffer *,
                          const char *);
    void answerCommandRequest(const char *);
    bool answerLogwatchCommandRequest(const char *);
};

#endif  // Store_h
