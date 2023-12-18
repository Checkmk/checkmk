// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Store_h
#define Store_h

#include <cstddef>
#include <map>
#include <string>
#include <vector>

#include "livestatus/LogCache.h"
#include "livestatus/TableColumns.h"
#include "livestatus/TableCommands.h"
#include "livestatus/TableComments.h"
#include "livestatus/TableContactGroups.h"
#include "livestatus/TableContacts.h"
#include "livestatus/TableCrashReports.h"
#include "livestatus/TableDowntimes.h"
#include "livestatus/TableDummy.h"
#include "livestatus/TableEventConsoleEvents.h"
#include "livestatus/TableEventConsoleHistory.h"
#include "livestatus/TableEventConsoleReplication.h"
#include "livestatus/TableEventConsoleRules.h"
#include "livestatus/TableEventConsoleStatus.h"
#include "livestatus/TableHostGroups.h"
#include "livestatus/TableHosts.h"
#include "livestatus/TableHostsByGroup.h"
#include "livestatus/TableLabels.h"
#include "livestatus/TableLog.h"
#include "livestatus/TableServiceGroups.h"
#include "livestatus/TableServices.h"
#include "livestatus/TableServicesByGroup.h"
#include "livestatus/TableServicesByHostGroup.h"
#include "livestatus/TableStateHistory.h"
#include "livestatus/TableStatus.h"
#include "livestatus/TableTimeperiods.h"
class ICore;
class Logger;
class OutputBuffer;
class Table;

class Store {
public:
    explicit Store(ICore *mc);
    [[nodiscard]] Logger *logger() const;
    size_t numCachedLogMessages();
    bool answerGetRequest(const std::vector<std::string> &lines,
                          OutputBuffer &output, const std::string &tablename);
    void addTable(Table &table);

    // NOTE: This is a cruel but temporary hack...
    TableStateHistory &getTableStateHistory() { return _table_statehistory; }

private:
    ICore *_mc;
    LogCache _log_cache;

    TableColumns _table_columns;
    TableCommands _table_commands;
    TableComments _table_comments;
    TableContactGroups _table_contactgroups;
    TableContacts _table_contacts;
    TableCrashReports _table_crash_reports;
    TableDowntimes _table_downtimes;
    TableEventConsoleEvents _table_eventconsoleevents;
    TableEventConsoleHistory _table_eventconsolehistory;
    TableEventConsoleReplication _table_eventconsolereplication;
    TableEventConsoleRules _table_eventconsolerules;
    TableEventConsoleStatus _table_eventconsolestatus;
    TableHostGroups _table_hostgroups;
    TableHosts _table_hosts;
    TableHostsByGroup _table_hostsbygroup;
    TableLabels _table_labels;
    TableLog _table_log;
    TableServiceGroups _table_servicegroups;
    TableServices _table_services;
    TableServicesByGroup _table_servicesbygroup;
    TableServicesByHostGroup _table_servicesbyhostgroup;
    TableStateHistory _table_statehistory;
    TableStatus _table_status;
    TableTimeperiods _table_timeperiods;
    TableDummy _table_dummy;

    std::map<std::string, Table *> _tables;

    Table &findTable(OutputBuffer &output, const std::string &name);
};

#endif  // Store_h
