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
#include <cstddef>
#include <list>
#include <map>
#include <string>
#ifndef CMC
#include <utility>
#include <vector>
#endif
#include "LogCache.h"
#include "Table.h"
#include "TableColumns.h"
#include "TableCommands.h"
#include "TableComments.h"
#include "TableContactGroups.h"
#include "TableContacts.h"
#include "TableCrashReports.h"
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
class Query;
class InputBuffer;
class Logger;
class MonitoringCore;
class OutputBuffer;

#ifdef CMC
#include <cstdint>
#include "TableCachedStatehist.h"
class Core;
class Object;
#else
#include <mutex>
#include "DowntimesOrComments.h"
#include "nagios.h"
#endif

class Store {
public:
#ifdef CMC
    Store(MonitoringCore *mc, Core *core);
    LogCache *logCache() { return &_log_cache; };
    bool answerRequest(InputBuffer *, OutputBuffer *);
    bool answerGetRequest(const std::list<std::string> &lines,
                          OutputBuffer &output, const std::string &tablename);
    void answerCommandRequest(const char *command, Logger *logger);
    void switchStatehistTable();
    void buildStatehistCache();
    void flushStatehistCache();
    void tryFinishStatehistCache();
    bool addObjectHistcache(Object *object);
    void addAlertToStatehistCache(Object *object, int state,
                                  const std::string &output,
                                  const std::string &long_output);
    void addDowntimeToStatehistCache(Object *object, bool started);
    void addFlappingToStatehistCache(Object *object, bool started);
#else
    explicit Store(MonitoringCore *mc);
    bool answerRequest(InputBuffer &input, OutputBuffer &output);

    void registerDowntime(nebstruct_downtime_data *data);
    void registerComment(nebstruct_comment_data *data);
#endif
    [[nodiscard]] Logger *logger() const;
    size_t numCachedLogMessages();

private:
    struct TableDummy : public Table {
        explicit TableDummy(MonitoringCore *mc) : Table(mc) {}
        [[nodiscard]] std::string name() const override { return "dummy"; }
        [[nodiscard]] std::string namePrefix() const override {
            return "dummy_";
        }
        void answerQuery(Query * /*unused*/) override {}
    };

    MonitoringCore *_mc;
#ifdef CMC
    Core *_core;
#endif
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

#ifndef CMC
    // Nagios is not thread-safe, so this mutex protects calls to
    // process_external_command1 / submit_external_command.
    std::mutex _command_mutex;
#endif

    void addTable(Table &table);
    Table &findTable(OutputBuffer &output, const std::string &name);
#ifdef CMC
    uint32_t horizon() const;
#else
    void logRequest(const std::string &line,
                    const std::list<std::string> &lines);
    bool answerGetRequest(const std::list<std::string> &lines,
                          OutputBuffer &output, const std::string &tablename);

    class ExternalCommand {
    public:
        explicit ExternalCommand(const std::string &str);
        [[nodiscard]] ExternalCommand withName(const std::string &name) const;
        [[nodiscard]] std::string name() const { return _name; }
        [[nodiscard]] std::string arguments() const { return _arguments; }
        [[nodiscard]] std::string str() const;
        [[nodiscard]] std::vector<std::string> args() const;

    private:
        std::string _prefix;  // including brackets and space
        std::string _name;
        std::string _arguments;

        ExternalCommand(std::string prefix, std::string name,
                        std::string arguments)
            : _prefix(std::move(prefix))
            , _name(std::move(name))
            , _arguments(std::move(arguments)) {}
    };

    void answerCommandRequest(const ExternalCommand &command);
    void answerCommandMkLogwatchAcknowledge(const ExternalCommand &command);
    void answerCommandDelCrashReport(const ExternalCommand &command);
    void answerCommandEventConsole(const ExternalCommand &command);
    void answerCommandNagios(const ExternalCommand &command);
#endif
};

#endif  // Store_h
