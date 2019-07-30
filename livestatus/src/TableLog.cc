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

#include "TableLog.h"
#include <bitset>
#include <cstdint>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <utility>
#include "Column.h"
#include "LogCache.h"
#include "LogEntry.h"
#include "Logfile.h"
#include "MonitoringCore.h"
#include "OffsetIntColumn.h"
#include "OffsetSStringColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "Row.h"
#include "TableCommands.h"
#include "TableContacts.h"
#include "TableHosts.h"
#include "TableServices.h"

#ifdef CMC
#include "cmc.h"
#else
#include "auth.h"
#include "nagios.h"
#endif

struct LogRow {
    LogEntry *entry;
    host *hst;
    service *svc;
    // cppcheck is too dumb to see usage in the DANGEROUS_OFFSETOF macro
    // cppcheck-suppress unusedStructMember
    const contact *ctc;
    Command command;
};

TableLog::TableLog(MonitoringCore *mc, LogCache *log_cache)
    : Table(mc), _log_cache(log_cache) {
    auto entry_offset = DANGEROUS_OFFSETOF(LogRow, entry);
    addColumn(std::make_unique<OffsetTimeColumn>(
        "time", "Time of the log event (UNIX timestamp)", entry_offset, -1, -1,
        DANGEROUS_OFFSETOF(LogEntry, _time)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "lineno", "The number of the line in the log file", entry_offset, -1,
        -1, DANGEROUS_OFFSETOF(LogEntry, _lineno)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "class",
        "The class of the message as integer (0:info, 1:state, 2:program, 3:notification, 4:passive, 5:command)",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _class)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "message", "The complete message line including the timestamp",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _message)));
    addColumn(std::make_unique<OffsetStringColumn>(
        "type",
        "The type of the message (text before the colon), the message itself for info messages",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _type)));
    addColumn(std::make_unique<OffsetStringColumn>(
        "options", "The part of the message after the ':'", entry_offset, -1,
        -1, DANGEROUS_OFFSETOF(LogEntry, _options)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "comment", "A comment field used in various message types",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _comment)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "plugin_output",
        "The output of the check, if any is associated with the message",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _plugin_output)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "long_plugin_output",
        "The complete output of the check, if any is associated with the message",
        entry_offset, -1, -1,
        DANGEROUS_OFFSETOF(LogEntry, _long_plugin_output)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "state", "The state of the host or service in question", entry_offset,
        -1, -1, DANGEROUS_OFFSETOF(LogEntry, _state)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "state_type", "The type of the state (varies on different log classes)",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _state_type)));
    addColumn(std::make_unique<OffsetIntColumn>(
        "attempt", "The number of the check attempt", entry_offset, -1, -1,
        DANGEROUS_OFFSETOF(LogEntry, _attempt)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "service_description",
        "The description of the service log entry is about (might be empty)",
        entry_offset, -1, -1,
        DANGEROUS_OFFSETOF(LogEntry, _service_description)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "host_name",
        "The name of the host the log entry is about (might be empty)",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _host_name)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "contact_name",
        "The name of the contact the log entry is about (might be empty)",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _contact_name)));
    addColumn(std::make_unique<OffsetSStringColumn>(
        "command_name",
        "The name of the command of the log entry (e.g. for notifications)",
        entry_offset, -1, -1, DANGEROUS_OFFSETOF(LogEntry, _command_name)));

    // join host and service tables
    TableHosts::addColumns(this, "current_host_",
                           DANGEROUS_OFFSETOF(LogRow, hst), -1);
    TableServices::addColumns(this, "current_service_",
                              DANGEROUS_OFFSETOF(LogRow, svc),
                              false /* no hosts table */);
    TableContacts::addColumns(this, "current_contact_",
                              DANGEROUS_OFFSETOF(LogRow, ctc));
    TableCommands::addColumns(this, "current_command_",
                              DANGEROUS_OFFSETOF(LogRow, command));
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
        auto entries =
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
        auto entry = it->second.get();
        // TODO(sp): Remove ugly casts.
        LogRow lr{
            entry,
            reinterpret_cast<host *>(core()->find_host(entry->_host_name)),
            reinterpret_cast<service *>(core()->find_service(
                entry->_host_name, entry->_service_description)),
            reinterpret_cast<const contact *>(
                core()->find_contact(entry->_contact_name)),
            core()->find_command(entry->_command_name)};
        if (!query->processDataset(Row(&lr))) {
            return false;
        }
    }
    return true;
}

bool TableLog::isAuthorized(Row row, const contact *ctc) const {
    auto lr = rowData<LogRow>(row);
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
