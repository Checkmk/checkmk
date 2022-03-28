// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableLog.h"

#include <bitset>
#include <chrono>
#include <cstdint>
#include <optional>
#include <stdexcept>

#include "Column.h"
#include "IntColumn.h"
#include "LogEntry.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "StringColumn.h"
#include "TableCommands.h"
#include "TableContacts.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "TimeColumn.h"
#include "auth.h"
#include "contact_fwd.h"

#ifdef CMC
#include "cmc.h"
class Contact;
class Host;
class Service;
#else
#include "nagios.h"
#endif

namespace {

class LogRow {
public:
    // TODO(sp): Remove ugly casts.
    LogRow(const LogEntry &entry_, MonitoringCore *mc)
        : entry{&entry_}
        , hst{reinterpret_cast<host *>(mc->find_host(entry_.host_name()))}
        , svc{reinterpret_cast<service *>(mc->find_service(
              entry_.host_name(), entry_.service_description()))}
        , ctc{reinterpret_cast<const contact *>(
              mc->find_contact(entry_.contact_name()))}
        , command{mc->find_command(entry_.command_name())} {}

    const LogEntry *entry;
    host *hst;
    service *svc;
    const contact *ctc;
    Command command;
};

}  // namespace

TableLog::TableLog(MonitoringCore *mc, LogCache *log_cache)
    : Table(mc), _log_cache(log_cache) {
    ColumnOffsets offsets{};
    auto offsets_entry{
        offsets.add([](Row r) { return r.rawData<LogRow>()->entry; })};
    addColumn(std::make_unique<TimeColumn<LogEntry>>(
        "time", "Time of the log event (UNIX timestamp)", offsets_entry,
        [](const LogEntry &r) { return r.time(); }));
    addColumn(std::make_unique<IntColumn<LogEntry>>(
        "lineno", "The number of the line in the log file", offsets_entry,
        [](const LogEntry &r) { return r.lineno(); }));
    addColumn(std::make_unique<IntColumn<LogEntry>>(
        "class",
        "The class of the message as integer (0:info, 1:state, 2:program, 3:notification, 4:passive, 5:command)",
        offsets_entry,
        [](const LogEntry &r) { return static_cast<int32_t>(r.log_class()); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "message", "The complete message line including the timestamp",
        offsets_entry, [](const LogEntry &r) { return r.message(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "type",
        "The type of the message (text before the colon), the message itself for info messages",
        offsets_entry, [](const LogEntry &r) { return r.type(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "options", "The part of the message after the ':'", offsets_entry,
        [](const LogEntry &r) { return r.options(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "comment", "A comment field used in various message types",
        offsets_entry, [](const LogEntry &r) { return r.comment(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "plugin_output",
        "The output of the check, if any is associated with the message",
        offsets_entry, [](const LogEntry &r) { return r.plugin_output(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "long_plugin_output",
        "The complete output of the check, if any is associated with the message",
        offsets_entry,
        [](const LogEntry &r) { return r.long_plugin_output(); }));
    addColumn(std::make_unique<IntColumn<LogEntry>>(
        "state", "The state of the host or service in question", offsets_entry,
        [](const LogEntry &r) { return r.state(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "state_type", "The type of the state (varies on different log classes)",
        offsets_entry, [](const LogEntry &r) { return r.state_type(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "state_info", "Additional information about the state", offsets_entry,
        [](const LogEntry &r) { return r.state_info(); }));
    addColumn(std::make_unique<IntColumn<LogEntry>>(
        "attempt", "The number of the check attempt", offsets_entry,
        [](const LogEntry &r) { return r.attempt(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "service_description",
        "The description of the service log entry is about (might be empty)",
        offsets_entry,
        [](const LogEntry &r) { return r.service_description(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "host_name",
        "The name of the host the log entry is about (might be empty)",
        offsets_entry, [](const LogEntry &r) { return r.host_name(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "contact_name",
        "The name of the contact the log entry is about (might be empty)",
        offsets_entry, [](const LogEntry &r) { return r.contact_name(); }));
    addColumn(std::make_unique<StringColumn<LogEntry>>(
        "command_name",
        "The name of the command of the log entry (e.g. for notifications)",
        offsets_entry, [](const LogEntry &r) { return r.command_name(); }));

    // join host and service tables
    TableHosts::addColumns(this, "current_host_", offsets.add([](Row r) {
        return r.rawData<LogRow>()->hst;
    }));
    TableServices::addColumns(this, "current_service_", offsets.add([](Row r) {
        return r.rawData<LogRow>()->svc;
    }),
                              false /* no hosts table */);
    TableContacts::addColumns(this, "current_contact_", offsets.add([](Row r) {
        return r.rawData<LogRow>()->ctc;
    }));
    TableCommands::addColumns(this, "current_command_", offsets.add([](Row r) {
        return &r.rawData<LogRow>()->command;
    }));
}

std::string TableLog::name() const { return "log"; }

std::string TableLog::namePrefix() const { return "log_"; }

namespace {
bool rowWithoutHost(const LogRow &lr) {
    auto clazz = lr.entry->log_class();
    return clazz == LogEntry::Class::info ||
           clazz == LogEntry::Class::program ||
           clazz == LogEntry::Class::ext_command;
}
}  // namespace

void TableLog::answerQuery(Query *query) {
    auto log_filter = constructFilter(query, core()->maxLinesPerLogFile());
    if (log_filter.classmask == 0) {
        return;
    }

    auto is_authorized = [service_auth = core()->serviceAuthorization(),
                          auth_user = query->authUser()](const LogRow &lr) {
        // If we have an AuthUser, suppress entries for messages with hosts that
        // do not exist anymore, otherwise use the common authorization logic.
        return lr.hst == nullptr  //
                   ? auth_user == no_auth_user() || rowWithoutHost(lr)
                   : lr.svc == nullptr
                         ? is_authorized_for_hst(auth_user, lr.hst)
                         : is_authorized_for_svc(service_auth, auth_user,
                                                 lr.svc);
    };

    auto process = [is_authorized, core = core(),
                    query](const LogEntry &entry) {
        LogRow r{entry, core};
        return !is_authorized(r) || query->processDataset(Row{&r});
    };
    _log_cache->for_each(log_filter, process);
}

// static
LogFilter TableLog::constructFilter(Query *query,
                                    size_t max_lines_per_logfile) {
    // Optimize time interval for the query. In log querys there should always
    // be a time range in form of one or two filter expressions over time. We
    // use that to limit the number of logfiles we need to scan and to find the
    // optimal entry point into the logfile
    auto since = std::chrono::system_clock::from_time_t(
        query->greatestLowerBoundFor("time").value_or(0));
    auto now =
        std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    auto until = std::chrono::system_clock::from_time_t(
        query->leastUpperBoundFor("time").value_or(now) + 1);

    // The second optimization is for log message types. We want to load only
    // those log type that are queried.
    auto classmask =
        static_cast<unsigned>(query->valueSetLeastUpperBoundFor("class")
                                  .value_or(~std::bitset<32>())
                                  .to_ulong());
    return {
        .max_lines_per_logfile = max_lines_per_logfile,
        .classmask = classmask,
        .since = since,
        .until = until,
    };
}

std::shared_ptr<Column> TableLog::column(std::string colname) const {
    try {
        // First try to find column in the usual way
        return Table::column(colname);
    } catch (const std::runtime_error &e) {
        // Now try with prefix "current_", since our joined tables have this
        // prefix in order to make clear that we access current and not historic
        // data and in order to prevent mixing up historic and current fields
        // with the same name.
        return Table::column("current_" + colname);
    }
}
