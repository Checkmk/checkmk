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
#include <string>
#ifndef CMC
#include <vector>
#endif
#include "LogCache.h"
#include "TableColumns.h"
#include "TableCommands.h"
#include "TableComments.h"
#include "TableContactGroups.h"
#include "TableContacts.h"
#include "TableDowntimes.h"
#include "TableEventConsoleEvents.h"
#include "TableEventConsoleHistory.h"
#include "TableEventConsoleReplication.h"
#include "TableEventConsoleRules.h"
#include "TableEventConsoleStatus.h"
#include "TableHostGroups.h"
#include "TableHosts.h"
#include "TableHostsByGroup.h"
#include "TableLog.h"
#include "TableServiceGroups.h"
#include "TableServices.h"
#include "TableServicesByGroup.h"
#include "TableServicesByHostGroup.h"
#include "TableStateHistory.h"
#include "TableStatus.h"
#include "TableTimeperiods.h"
class InputBuffer;
class Logger;
class MonitoringCore;
class OutputBuffer;
class Table;

#ifdef CMC
#include <cstdint>
#include "TableCachedStatehist.h"
class Config;
class Object;
#else
#include <mutex>
#include "DowntimesOrComments.h"
#include "nagios.h"
#endif

class Store {
public:
    explicit Store(MonitoringCore *mc);
#ifdef CMC
    LogCache *logCache() { return &_log_cache; };
    bool answerRequest(InputBuffer *, OutputBuffer *);
    bool answerGetRequest(const std::list<std::string> &lines,
                          OutputBuffer &output, const std::string &tablename);
    void answerCommandRequest(const char *command, Logger *logger);
    void setMaxCachedMessages(unsigned long m);
    void switchStatehistTable();
    void buildStatehistCache();
    void flushStatehistCache();
    void tryFinishStatehistCache();
    bool addObjectHistcache(Object *);
    void addAlertToStatehistCache(Object *, int state, const char *output);
    void addDowntimeToStatehistCache(Object *, bool started);
    void addFlappingToStatehistCache(Object *, bool started);
#else
    bool answerRequest(InputBuffer &input, OutputBuffer &output);

    void registerDowntime(nebstruct_downtime_data *);
    void registerComment(nebstruct_comment_data *);
#endif
    Logger *logger() const;

private:
    MonitoringCore *_mc;
#ifndef CMC
    // TODO(sp) These fields should better be somewhere else, e.g. module.cc
public:
    DowntimesOrComments _downtimes;
    DowntimesOrComments _comments;

private:
#endif
    LogCache _log_cache;

#ifdef CMC
    TableCachedStatehist _table_cached_statehist;
#endif
    TableColumns _table_columns;
    TableCommands _table_commands;
    TableComments _table_comments;
    TableContactGroups _table_contactgroups;
    TableContacts _table_contacts;
    TableDowntimes _table_downtimes;
    TableEventConsoleEvents _table_eventconsoleevents;
    TableEventConsoleHistory _table_eventconsolehistory;
    TableEventConsoleReplication _table_eventconsolereplication;
    TableEventConsoleRules _table_eventconsolerules;
    TableEventConsoleStatus _table_eventconsolestatus;
    TableHostGroups _table_hostgroups;
    TableHosts _table_hosts;
    TableHostsByGroup _table_hostsbygroup;
    TableLog _table_log;
    TableServiceGroups _table_servicegroups;
    TableServices _table_services;
    TableServicesByGroup _table_servicesbygroup;
    TableServicesByHostGroup _table_servicesbyhostgroup;
    TableStateHistory _table_statehistory;
    TableStatus _table_status;
    TableTimeperiods _table_timeperiods;

    std::map<std::string, Table *> _tables;

#ifndef CMC
    // Nagios is not thread-safe, so this mutex protects calls to
    // process_external_command1 / submit_external_command.
    std::mutex _command_mutex;
#endif

    void addTable(Table *table);
    Table *findTable(const std::string &name);
#ifdef CMC
    const Config *config() const;
    uint32_t horizon() const;
#else
    void logRequest(const std::string &line,
                    const std::list<std::string> &lines);
    bool answerGetRequest(const std::list<std::string> &lines,
                          OutputBuffer &output, const std::string &tablename);

    class ExternalCommand {
    public:
        explicit ExternalCommand(const std::string &str);
        ExternalCommand withName(const std::string &name) const;
        std::string name() const { return _name; }
        std::string arguments() const { return _arguments; }
        std::string str() const;
        std::vector<std::string> args() const;

    private:
        std::string _prefix;  // including brackets and space
        std::string _name;
        std::string _arguments;

        ExternalCommand(const std::string &prefix, const std::string &name,
                        const std::string &arguments)
            : _prefix(prefix), _name(name), _arguments(arguments) {}
    };

    void answerCommandRequest(const ExternalCommand &command);
    void answerCommandMkLogwatchAcknowledge(const ExternalCommand &command);
    void answerCommandEventConsole(const ExternalCommand &command);
    void answerCommandNagios(const ExternalCommand &command);
#endif
};

#endif  // Store_h
