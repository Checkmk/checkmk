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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "Store.h"
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include <utility>
#include "InputBuffer.h"
#include "OutputBuffer.h"
#include "Query.h"
#include "Table.h"
#include "global_counters.h"
#include "logger.h"
#include "strutil.h"

// TODO(sp): Remove this hack.
#ifdef EXTERN
#undef EXTERN
#endif
#define EXTERN
#include "tables.h"  // IWYU pragma: keep
#undef EXTERN

using mk::lock_guard;
using mk::mutex;
using std::list;
using std::make_pair;
using std::pair;
using std::string;

extern int g_debug_level;
extern unsigned long g_max_cached_messages;

Store::Store()
    : _log_cache(g_max_cached_messages)
    , _table_hosts(false)
    , _table_hostsbygroup(true)
    , _table_services(false, false)
    , _table_servicesbygroup(true, false)
    , _table_servicesbyhostgroup(false, true)
    , _table_downtimes(true)
    , _table_comments(false)
    , _table_log(&_log_cache)
    , _table_statehistory(&_log_cache) {
    _tables.insert(make_pair("columns", &_table_columns));
    _tables.insert(make_pair("commands", &_table_commands));
    _tables.insert(make_pair("comments", &_table_comments));
    _tables.insert(make_pair("contactgroups", &_table_contactgroups));
    _tables.insert(make_pair("contacts", &_table_contacts));
    _tables.insert(make_pair("downtimes", &_table_downtimes));
    _tables.insert(make_pair("hostgroups", &_table_hostgroups));
    _tables.insert(make_pair("hostsbygroup", &_table_hostsbygroup));
    _tables.insert(make_pair("hosts", &_table_hosts));
    _tables.insert(make_pair("log", &_table_log));
    _tables.insert(make_pair("servicegroups", &_table_servicegroups));
    _tables.insert(make_pair("servicesbygroup", &_table_servicesbygroup));
    _tables.insert(
        make_pair("servicesbyhostgroup", &_table_servicesbyhostgroup));
    _tables.insert(make_pair("services", &_table_services));
    _tables.insert(make_pair("statehist", &_table_statehistory));
    _tables.insert(make_pair("status", &_table_status));
    _tables.insert(make_pair("timeperiods", &_table_timeperiods));

    g_table_hosts = &_table_hosts;
    g_table_services = &_table_services;
    g_table_servicesbygroup = &_table_servicesbygroup;
    g_table_servicesbyhostgroup = &_table_servicesbyhostgroup;
    g_table_hostgroups = &_table_hostgroups;
    g_table_servicegroups = &_table_servicegroups;
    g_table_contacts = &_table_contacts;
    g_table_commands = &_table_commands;
    g_table_downtimes = &_table_downtimes;
    g_table_comments = &_table_comments;
    g_table_status = &_table_status;
    g_table_timeperiods = &_table_timeperiods;
    g_table_contactgroups = &_table_contactgroups;
    g_table_log = &_table_log;
    g_table_statehistory = &_table_statehistory;
    g_table_columns = &_table_columns;

    for (auto &table : _tables) {
        _table_columns.addTable(table.second);
    }
}

Store::~Store() = default;

Table *Store::findTable(string name) {
    auto it = _tables.find(name);
    if (it == _tables.end()) {
        return nullptr;
    }
    return it->second;
}

void Store::registerComment(nebstruct_comment_data *d) {
    _table_comments.addComment(d);
}

void Store::registerDowntime(nebstruct_downtime_data *d) {
    _table_downtimes.addDowntime(d);
}

namespace {
list<string> getLines(InputBuffer *input) {
    list<string> lines;
    while (!input->empty()) {
        lines.push_back(input->nextLine());
        if (lines.back().empty()) {
            break;
        }
    }
    return lines;
}
}  // namespace

bool Store::answerRequest(InputBuffer *input, OutputBuffer *output) {
    output->reset();
    InputBuffer::Result res = input->readRequest();
    if (res != InputBuffer::Result::request_read) {
        if (res != InputBuffer::Result::eof) {
            output->setError(
                RESPONSE_CODE_INCOMPLETE_REQUEST,
                "Client connection terminated while request still incomplete");
        }
        return false;
    }
    string l = input->nextLine();
    const char *line = l.c_str();
    if (g_debug_level > 0) {
        logger(LG_INFO, "Query: %s", line);
    }
    if (strncmp(line, "GET ", 4) == 0) {
        answerGetRequest(getLines(input), output,
                         lstrip(const_cast<char *>(line) + 4));
    } else if (strcmp(line, "GET") == 0) {
        // only to get error message
        answerGetRequest(getLines(input), output, "");
    } else if (strncmp(line, "COMMAND ", 8) == 0) {
        answerCommandRequest(lstrip(const_cast<char *>(line) + 8));
        output->setDoKeepalive(true);
    } else if (strncmp(line, "LOGROTATE", 9) == 0) {
        logger(LG_INFO, "Forcing logfile rotation");
        rotate_log_file(time(nullptr));
        schedule_new_event(EVENT_LOG_ROTATION, 1, get_next_log_rotation_time(),
                           0, 0,
                           reinterpret_cast<void *>(get_next_log_rotation_time),
                           1, nullptr, nullptr, 0);
    } else {
        logger(LG_INFO, "Invalid request '%s'", line);
        output->setError(RESPONSE_CODE_INVALID_REQUEST,
                         "Invalid request method");
    }
    return output->doKeepalive();
}

void Store::answerCommandRequest(const char *command) {
    lock_guard<mutex> lg(_command_mutex);
#ifdef NAGIOS4
    process_external_command1((char *)command);
#else
    int buffer_items = -1;
    /* int ret = */
    submit_external_command(const_cast<char *>(command), &buffer_items);
#endif
}

void Store::answerGetRequest(const list<string> &lines, OutputBuffer *output,
                             const char *tablename) {
    output->reset();
    if (tablename[0] == 0) {
        output->setError(RESPONSE_CODE_INVALID_REQUEST,
                         "Invalid GET request, missing tablename");
    }
    Table *table = findTable(tablename);
    if (table == nullptr) {
        output->setError(RESPONSE_CODE_NOT_FOUND,
                         "Invalid GET request, no such table '%s'", tablename);
    }
    Query query(lines, output, table);

    if ((table != nullptr) && !output->hasError()) {
        if (query.hasNoColumns()) {
            table->addAllColumnsToQuery(&query);
            query.setShowColumnHeaders(true);
        }
        struct timeval before, after;
        gettimeofday(&before, nullptr);
        query.start();
        table->answerQuery(&query);
        query.finish();
        gettimeofday(&after, nullptr);
        unsigned long ustime = (after.tv_sec - before.tv_sec) * 1000000 +
                               (after.tv_usec - before.tv_usec);
        if (g_debug_level > 0) {
            logger(LG_INFO,
                   "Time to process request: %lu us. Size of answer: %d bytes",
                   ustime, output->size());
        }
    }
}
