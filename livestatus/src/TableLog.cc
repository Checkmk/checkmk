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
#include <cstdint>
#include <map>
#include <utility>
#include "Column.h"
#include "LogCache.h"
#include "LogEntry.h"
#include "Logfile.h"
#include "MonitoringCore.h"
#include "OffsetIntColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "TableCommands.h"
#include "TableContacts.h"
#include "TableHosts.h"
#include "TableServices.h"

#ifndef CMC
#include <mutex>
#include "auth.h"
#endif

using std::lock_guard;
using std::make_unique;
using std::mutex;
using std::shared_ptr;
using std::string;

TableLog::TableLog(LogCache *log_cache,
#ifdef CMC
                   const Downtimes &downtimes_holder,
                   const Comments &comments_holder,
                   std::recursive_mutex &holder_lock, Core *core
#else
                   const DowntimesOrComments &downtimes_holder,
                   const DowntimesOrComments &comments_holder
#endif
                   ,
                   MonitoringCore *mc)
    : Table(mc->loggerLivestatus()), _core(mc), _log_cache(log_cache) {
    LogEntry *ref = nullptr;
    addColumn(make_unique<OffsetTimeColumn>(
        "time", "Time of the log event (UNIX timestamp)",
        reinterpret_cast<char *>(&(ref->_time)) - reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "lineno", "The number of the line in the log file",
        reinterpret_cast<char *>(&(ref->_lineno)) -
            reinterpret_cast<char *>(ref),
        -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "class",
        "The class of the message as integer (0:info, 1:state, 2:program, "
        "3:notification, 4:passive, 5:command)",
        reinterpret_cast<char *>(&(ref->_logclass)) -
            reinterpret_cast<char *>(ref),
        -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "message", "The complete message line including the timestamp",
        reinterpret_cast<char *>(&(ref->_complete)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "type",
        "The type of the message (text before the colon), the message itself "
        "for info messages",
        reinterpret_cast<char *>(&(ref->_text)) - reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "options", "The part of the message after the ':'",
        reinterpret_cast<char *>(&(ref->_options)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "comment", "A comment field used in various message types",
        reinterpret_cast<char *>(&(ref->_comment)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "plugin_output",
        "The output of the check, if any is associated with the message",
        reinterpret_cast<char *>(&(ref->_check_output)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "state", "The state of the host or service in question",
        reinterpret_cast<char *>(&(ref->_state)) -
            reinterpret_cast<char *>(ref),
        -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "state_type", "The type of the state (varies on different log classes)",
        reinterpret_cast<char *>(&(ref->_state_type)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetIntColumn>(
        "attempt", "The number of the check attempt",
        reinterpret_cast<char *>(&(ref->_attempt)) -
            reinterpret_cast<char *>(ref),
        -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "service_description",
        "The description of the service log entry is about (might be empty)",
        reinterpret_cast<char *>(&(ref->_svc_desc)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "host_name",
        "The name of the host the log entry is about (might be empty)",
        reinterpret_cast<char *>(&(ref->_host_name)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "contact_name",
        "The name of the contact the log entry is about (might be empty)",
        reinterpret_cast<char *>(&(ref->_contact_name)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));
    addColumn(make_unique<OffsetStringColumn>(
        "command_name",
        "The name of the command of the log entry (e.g. for notifications)",
        reinterpret_cast<char *>(&(ref->_command_name)) -
            reinterpret_cast<char *>(ref),
        -1, -1, -1));

    // join host and service tables
    TableHosts::addColumns(
        this, "current_host_",
        reinterpret_cast<char *>(&(ref->_host)) - reinterpret_cast<char *>(ref),
        -1, downtimes_holder, comments_holder
#ifdef CMC
        ,
        holder_lock, core
#else
        ,
        mc
#endif
        );
    TableServices::addColumns(
        this, "current_service_", reinterpret_cast<char *>(&(ref->_service)) -
                                      reinterpret_cast<char *>(ref),
        false /* no hosts table */, downtimes_holder, comments_holder
#ifdef CMC
        ,
        holder_lock, core
#else
        ,
        mc
#endif
        );
    TableContacts::addColumns(this, "current_contact_",
                              reinterpret_cast<char *>(&(ref->_contact)) -
                                  reinterpret_cast<char *>(ref));
    TableCommands::addColumns(this, "current_command_",
                              reinterpret_cast<char *>(&(ref->_command)) -
                                  reinterpret_cast<char *>(ref));
}

string TableLog::name() const { return "log"; }

string TableLog::namePrefix() const { return "log_"; }

void TableLog::answerQuery(Query *query) {
    lock_guard<mutex> lg(_log_cache->_lock);
    if (!_log_cache->logCachePreChecks(_core)) {
        return;
    }

    int since = 0;
    int until = time(nullptr) + 1;
    // Optimize time interval for the query. In log querys
    // there should always be a time range in form of one
    // or two filter expressions over time. We use that
    // to limit the number of logfiles we need to scan and
    // to find the optimal entry point into the logfile
    query->findIntLimits("time", &since, &until);

    // The second optimization is for log message types.
    // We want to load only those log type that are queried.
    uint32_t classmask = LogEntry::all_classes;
    query->optimizeBitmask("class", &classmask);
    if (classmask == 0) {
        return;
    }

    /* This code start with the oldest log entries. I'm going
       to change this and start with the newest. That way,
       the Limit: header produces more reasonable results. */

    /* NEW CODE - NEWEST FIRST */
    _logfiles_t::iterator it;
    it = _log_cache->logfiles()->end();  // it now points beyond last log file
    --it;  // switch to last logfile (we have at least one)

    // Now find newest log where 'until' is contained. The problem
    // here: For each logfile we only know the time of the *first* entry,
    // not that of the last.
    while (it != _log_cache->logfiles()->begin() &&
           it->first > until) {  // while logfiles are too new...
        --it;                    // go back in history
    }
    if (it->first > until) {
        return;  // all logfiles are too new
    }

    while (true) {
        Logfile *log = it->second;
        if (!log->answerQueryReverse(query, _log_cache, since, until,
                                     classmask)) {
            break;  // end of time range found
        }
        if (it == _log_cache->logfiles()->begin()) {
            break;  // this was the oldest one
        }
        --it;
    }
}

bool TableLog::isAuthorized(contact *ctc, void *data) {
    LogEntry *entry = static_cast<LogEntry *>(data);
    service *svc = entry->_service;
    host *hst = entry->_host;

    if ((hst != nullptr) || (svc != nullptr)) {
        return is_authorized_for(ctc, hst, svc);
        // suppress entries for messages that belong to hosts that do not exist
        // anymore.
    }
    return !(entry->_logclass == LogEntry::Class::alert ||
             entry->_logclass == LogEntry::Class::hs_notification ||
             entry->_logclass == LogEntry::Class::passivecheck ||
             entry->_logclass == LogEntry::Class::alert_handlers ||
             entry->_logclass == LogEntry::Class::state);
}

shared_ptr<Column> TableLog::column(string colname) {
    // First try to find column in the usual way
    if (auto col = Table::column(colname)) {
        return col;
    }

    // Now try with prefix "current_", since our joined
    // tables have this prefix in order to make clear that
    // we access current and not historic data and in order
    // to prevent mixing up historic and current fields with
    // the same name.
    return Table::column(string("current_") + colname);
}
