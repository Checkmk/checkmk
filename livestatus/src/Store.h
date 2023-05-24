// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Store_h
#define Store_h

#include "config.h"  // IWYU pragma: keep

#include <cstddef>
#include <list>
#include <map>
#include <string>

#include "livestatus/LogCache.h"
#include "livestatus/Table.h"
#include "livestatus/TableColumns.h"
#include "livestatus/TableCommands.h"
#include "livestatus/TableComments.h"
#include "livestatus/TableContactGroups.h"
#include "livestatus/TableContacts.h"
#include "livestatus/TableCrashReports.h"
#include "livestatus/TableDowntimes.h"
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
class Query;
class User;

#ifdef CMC
#include <chrono>
#include <optional>

#include "TableCachedStatehist.h"
class Object;
#else
#include <mutex>
#include <utility>
#include <vector>
class InputBuffer;
#endif

class Store {
public:
#ifdef CMC
    Store(ICore *mc, std::optional<std::chrono::seconds> cache_horizon,
          Logger *logger);
    void switchStatehistTable(std::optional<std::chrono::seconds> cache_horizon,
                              Logger *logger);
    void buildStatehistCache(std::optional<std::chrono::seconds> cache_horizon);
    void flushStatehistCache();
    void tryFinishStatehistCache();
    void addObjectHistcache(std::optional<std::chrono::seconds> cache_horizon,
                            Object *object);
    void addAlertToStatehistCache(
        std::optional<std::chrono::seconds> cache_horizon, const Object &object,
        int state, const std::string &output, const std::string &long_output);
    void addDowntimeToStatehistCache(
        std::optional<std::chrono::seconds> cache_horizon, const Object &object,
        bool started);
    void addFlappingToStatehistCache(
        std::optional<std::chrono::seconds> cache_horizon, const Object &object,
        bool started);
#else
    explicit Store(ICore *mc);
    bool answerRequest(InputBuffer &input, OutputBuffer &output);
#endif
    [[nodiscard]] Logger *logger() const;
    size_t numCachedLogMessages();
    bool answerGetRequest(const std::list<std::string> &lines,
                          OutputBuffer &output, const std::string &tablename);

private:
    struct TableDummy : public Table {
        explicit TableDummy(ICore *mc) : Table(mc) {}
        [[nodiscard]] std::string name() const override { return "dummy"; }
        [[nodiscard]] std::string namePrefix() const override {
            return "dummy_";
        }
        void answerQuery(Query & /*unused*/, const User & /*user*/) override {}
    };

    ICore *_mc;
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

#ifndef CMC
    // Nagios is not thread-safe, so this mutex protects calls to
    // process_external_command1 / submit_external_command.
    std::mutex _command_mutex;
#endif

    void addTable(Table &table);
    Table &findTable(OutputBuffer &output, const std::string &name);
#ifndef CMC
    void logRequest(const std::string &line,
                    const std::list<std::string> &lines) const;

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
    void answerCommandEventConsole(const std::string &command);
    void answerCommandNagios(const ExternalCommand &command);
#endif
};

#endif  // Store_h
