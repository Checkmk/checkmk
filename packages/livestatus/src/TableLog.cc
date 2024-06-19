// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableLog.h"

#include <bitset>
#include <chrono>
#include <compare>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <map>
#include <optional>
#include <stdexcept>
#include <utility>

#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/LogCache.h"
#include "livestatus/LogEntry.h"
#include "livestatus/Logfile.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TableCommands.h"
#include "livestatus/TableContacts.h"
#include "livestatus/TableHosts.h"
#include "livestatus/TableServices.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/User.h"
class IContact;
class IHost;
class IService;

namespace {
class LogRow {
public:
    LogRow(const LogEntry &entry_, const ICore &core)
        : entry{&entry_}
        , hst{core.find_host(entry_.host_name())}
        , svc{core.find_service(entry_.host_name(),
                                entry_.service_description())}
        , ctc{core.find_contact(entry_.contact_name())}
        , command{core.find_command(entry_.command_name())} {}

    const LogEntry *entry;
    const IHost *hst;
    const IService *svc;
    const IContact *ctc;
    Command command;
};
}  // namespace

using row_type = LogRow;

TableLog::TableLog(ICore *mc, LogCache *log_cache) : log_cache_{log_cache} {
    const ColumnOffsets offsets{};
    auto offsets_entry{
        offsets.add([](Row r) { return r.rawData<row_type>()->entry; })};
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
    TableHosts::addColumns(this, *mc, "current_host_", offsets.add([](Row r) {
        return r.rawData<row_type>()->hst;
    }),
                           LockComments::yes, LockDowntimes::yes);
    TableServices::addColumns(
        this, *mc, "current_service_",
        offsets.add([](Row r) { return r.rawData<row_type>()->svc; }),
        TableServices::AddHosts::no, LockComments::yes, LockDowntimes::yes);
    TableContacts::addColumns(this, "current_contact_", offsets.add([](Row r) {
        return r.rawData<row_type>()->ctc;
    }));
    TableCommands::addColumns(this, "current_command_", offsets.add([](Row r) {
        return &r.rawData<row_type>()->command;
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

LogFilter constructFilter(Query &query, size_t max_lines_per_logfile) {
    // Figure out the time interval for the query: In log queries there should
    // always be a time range in the form of one or two filter expressions for
    // "time"". We use that to limit the number of log files we need to scan and
    // to find the optimal entry point into the log file.
    auto since = std::chrono::system_clock::from_time_t(
        query.greatestLowerBoundFor("time").value_or(0));
    auto now =
        std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    auto until = std::chrono::system_clock::from_time_t(
        query.leastUpperBoundFor("time").value_or(now) + 1);

    // The second optimization is for log entry classes: We want to load only
    // those entries with a class that is actually required.
    auto log_entry_classes =
        query.valueSetLeastUpperBoundFor("class").value_or(~std::bitset<32>{});

    return {
        .max_lines_per_log_file = max_lines_per_logfile,
        .log_entry_classes = log_entry_classes,
        .since = since,
        .until = until,
    };
}

// Call the given callback for each log entry matching the filter in a
// chronologically backwards fashion, until the callback returns false.
void for_each_log_entry(
    LogCache &log_cache, const LogFilter &log_filter,
    const std::function<bool(const LogEntry &)> &process_log_entry) {
    log_cache.apply(
        [&log_filter, &process_log_entry](const LogFiles &log_files,
                                          size_t /*num_cached_log_messages*/) {
            if (log_files.begin() == log_files.end()) {
                return;
            }
            auto it = log_files.end();  // it now points beyond last log file
            --it;  // switch to last logfile (we have at least one)

            // Now find newest log where 'until' is contained. The problem here:
            // For each logfile we only know the time of the *first* entry, not
            // that of the last.
            while (it != log_files.begin() &&
                   it->second->since() > log_filter.until) {
                --it;  // while logfiles are too new go back in history
            }
            if (it->second->since() > log_filter.until) {
                return;  // all logfiles are too new
            }

            while (true) {
                const auto *entries = it->second->getEntriesFor(
                    log_filter.max_lines_per_log_file,
                    log_filter.log_entry_classes.to_ulong());  // TODO(sp)
                if (!Logfile::processLogEntries(process_log_entry, entries,
                                                log_filter)) {
                    break;  // end of time range found
                }
                if (it == log_files.begin()) {
                    break;  // this was the oldest one
                }
                --it;
            }
        });
}

}  // namespace

void TableLog::answerQuery(Query &query, const User &user, const ICore &core) {
    auto log_filter = constructFilter(query, core.maxLinesPerLogFile());
    if (log_filter.log_entry_classes == 0) {  // optimization only
        return;
    }

    auto is_authorized = [&user](const row_type &row) {
        // If we have an AuthUser, suppress entries for messages with hosts
        // that do not exist anymore, otherwise use the common authorization
        // logic.
        return user.is_authorized_for_object(row.hst, row.svc,
                                             rowWithoutHost(row));
    };

    auto process = [is_authorized, &core, &query](const LogEntry &entry) {
        row_type row{entry, core};
        return !is_authorized(row) || query.processDataset(Row{&row});
    };
    for_each_log_entry(*log_cache_, log_filter, process);
}

std::shared_ptr<Column> TableLog::column(std::string colname) const {
    try {
        // First try to find column in the usual way
        return Table::column(colname);
    } catch (const std::runtime_error &e) {
        // Now try with prefix "current_", since our joined tables have this
        // prefix in order to make clear that we access current and not
        // historic data and in order to prevent mixing up historic and
        // current fields with the same name.
        return Table::column("current_" + colname);
    }
}
