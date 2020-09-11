// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableLog.h"

#include <bitset>
#include <chrono>
#include <cstdint>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <utility>

#include "Column.h"
#include "IntLambdaColumn.h"
#include "LogCache.h"
#include "LogEntry.h"
#include "LogEntryStringColumn.h"
#include "Logfile.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "StringLambdaColumn.h"
#include "TableCommands.h"
#include "TableContacts.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "TimeLambdaColumn.h"

#ifdef CMC
#include "cmc.h"
#else
#include "auth.h"
#include "nagios.h"
#endif

namespace {

class LogRow {
public:
    // cppcheck confuses "command" and "Command" below! o_O
    // cppcheck-suppress uninitMemberVar
    LogRow(LogEntry *entry_, host *hst_, service *svc_, const contact *ctc_,
           const Command *command_)
        : entry{entry_}, hst{hst_}, svc{svc_}, ctc{ctc_}, command{command_} {};

    LogEntry *entry;
    host *hst;
    service *svc;
    const contact *ctc;
    const Command *command;
};

}  // namespace

TableLog::TableLog(MonitoringCore *mc, LogCache *log_cache)
    : Table(mc), _log_cache(log_cache) {
    ColumnOffsets offsets{};
    auto offsets_entry{
        offsets.add([](Row r) { return r.rawData<LogRow>()->entry; })};
    addColumn(std::make_unique<TimeLambdaColumn<LogEntry>>(
        "time", "Time of the log event (UNIX timestamp)", offsets_entry,
        [](const LogEntry &r) {
            return std::chrono::system_clock::from_time_t(r._time);
        }));
    addColumn(std::make_unique<IntLambdaColumn<LogEntry>>(
        "lineno", "The number of the line in the log file", offsets_entry,
        [](const LogEntry &r) { return r._lineno; }));
    addColumn(std::make_unique<IntLambdaColumn<LogEntry>>(
        "class",
        "The class of the message as integer (0:info, 1:state, 2:program, 3:notification, 4:passive, 5:command)",
        offsets_entry,
        [](const LogEntry &r) { return static_cast<int32_t>(r._class); }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "message", "The complete message line including the timestamp",
        offsets_entry, [](const LogEntry &r) { return r._message; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "type",
        "The type of the message (text before the colon), the message itself for info messages",
        offsets_entry,
        [](const LogEntry &r) { return r._type == nullptr ? "" : r._type; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "options", "The part of the message after the ':'", offsets_entry,
        [](const LogEntry &r) {
            return r._options == nullptr ? "" : r._options;
        }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "comment", "A comment field used in various message types",
        offsets_entry, [](const LogEntry &r) { return r._comment; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "plugin_output",
        "The output of the check, if any is associated with the message",
        offsets_entry, [](const LogEntry &r) { return r._plugin_output; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "long_plugin_output",
        "The complete output of the check, if any is associated with the message",
        offsets_entry,
        [](const LogEntry &r) { return r._long_plugin_output; }));
    addColumn(std::make_unique<IntLambdaColumn<LogEntry>>(
        "state", "The state of the host or service in question", offsets_entry,
        [](const LogEntry &r) { return r._state; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "state_type", "The type of the state (varies on different log classes)",
        offsets_entry, [](const LogEntry &r) { return r._state_type; }));
    addColumn(std::make_unique<LogEntryStringColumn>(
        "state_info", "Additional information about the state", offsets_entry));
    addColumn(std::make_unique<IntLambdaColumn<LogEntry>>(
        "attempt", "The number of the check attempt", offsets_entry,
        [](const LogEntry &r) { return r._attempt; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "service_description",
        "The description of the service log entry is about (might be empty)",
        offsets_entry,
        [](const LogEntry &r) { return r._service_description; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "host_name",
        "The name of the host the log entry is about (might be empty)",
        offsets_entry, [](const LogEntry &r) { return r._host_name; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "contact_name",
        "The name of the contact the log entry is about (might be empty)",
        offsets_entry, [](const LogEntry &r) { return r._contact_name; }));
    addColumn(std::make_unique<StringLambdaColumn<LogEntry>>(
        "command_name",
        "The name of the command of the log entry (e.g. for notifications)",
        offsets_entry, [](const LogEntry &r) { return r._command_name; }));

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
        return r.rawData<LogRow>()->command;
    }));
}

std::string TableLog::name() const { return "log"; }

std::string TableLog::namePrefix() const { return "log_"; }

void TableLog::answerQuery(Query *query) {
    std::lock_guard<std::mutex> lg(_log_cache->_lock);
    _log_cache->update();
    if (_log_cache->begin() == _log_cache->end()) {
        return;
    }

    // Optimize time interval for the query. In log querys there should always
    // be a time range in form of one or two filter expressions over time. We
    // use that to limit the number of logfiles we need to scan and to find the
    // optimal entry point into the logfile
    int since = query->greatestLowerBoundFor("time").value_or(0);
    int until = query->leastUpperBoundFor("time").value_or(time(nullptr)) + 1;

    // The second optimization is for log message types. We want to load only
    // those log type that are queried.
    auto classmask = query->valueSetLeastUpperBoundFor("class")
                         .value_or(~std::bitset<32>())
                         .to_ulong();
    if (classmask == 0) {
        return;
    }

    /* This code start with the oldest log entries. I'm going
       to change this and start with the newest. That way,
       the Limit: header produces more reasonable results. */

    /* NEW CODE - NEWEST FIRST */
    auto it = _log_cache->end();  // it now points beyond last log file
    --it;  // switch to last logfile (we have at least one)

    // Now find newest log where 'until' is contained. The problem
    // here: For each logfile we only know the time of the *first* entry,
    // not that of the last.
    while (it != _log_cache->begin() && it->first > until) {
        // while logfiles are too new go back in history
        --it;
    }
    if (it->first > until) {
        return;  // all logfiles are too new
    }

    while (true) {
        const auto *entries =
            it->second->getEntriesFor(core()->maxLinesPerLogFile(), classmask);
        if (!answerQueryReverse(entries, query, since, until)) {
            break;  // end of time range found
        }
        if (it == _log_cache->begin()) {
            break;  // this was the oldest one
        }
        --it;
    }
}

bool TableLog::answerQueryReverse(const logfile_entries_t *entries,
                                  Query *query, time_t since, time_t until) {
    auto it = entries->upper_bound(Logfile::makeKey(until, 999999999));
    while (it != entries->begin()) {
        --it;
        if (it->second->_time < since) {
            return false;  // time limit exceeded
        }
        auto *entry = it->second.get();
        Command command = core()->find_command(entry->_command_name);
        // TODO(sp): Remove ugly casts.
        LogRow lr{
            entry,
            reinterpret_cast<host *>(core()->find_host(entry->_host_name)),
            reinterpret_cast<service *>(core()->find_service(
                entry->_host_name, entry->_service_description)),
            reinterpret_cast<const contact *>(
                core()->find_contact(entry->_contact_name)),
            &command};
        const LogRow *r = &lr;
        if (!query->processDataset(Row{r})) {
            return false;
        }
    }
    return true;
}

bool TableLog::isAuthorized(Row row, const contact *ctc) const {
    const auto *lr = rowData<LogRow>(row);
    service *svc = lr->svc;
    host *hst = lr->hst;

    if (hst != nullptr || svc != nullptr) {
        return is_authorized_for(core(), ctc, hst, svc);
        // suppress entries for messages that belong to hosts that do not exist
        // anymore.
    }
    auto clazz = lr->entry->_class;
    return !(clazz == LogEntry::Class::alert ||
             clazz == LogEntry::Class::hs_notification ||
             clazz == LogEntry::Class::passivecheck ||
             clazz == LogEntry::Class::alert_handlers ||
             clazz == LogEntry::Class::state);
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
