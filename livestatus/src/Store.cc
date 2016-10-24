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

#include "Store.h"
#include <chrono>
#include <cstring>
#include <ctime>
#include <ostream>
#include <utility>
#include "InputBuffer.h"
#include "Logger.h"
#include "OutputBuffer.h"
#include "Query.h"
#include "Table.h"
#include "data_encoding.h"
#include "mk_logwatch.h"
#include "strutil.h"

extern Encoding g_data_encoding;
extern unsigned long g_max_cached_messages;

using std::chrono::duration_cast;
using std::chrono::microseconds;
using std::chrono::system_clock;
using std::list;
using std::lock_guard;
using std::mutex;
using std::string;

Store::Store(Logger *logger)
    : _log_cache(_commands_holder, g_max_cached_messages)
    , _table_contacts(logger)
    , _table_commands(_commands_holder, logger)
    , _table_hostgroups(logger)
    , _table_hosts(_downtimes, _comments, logger)
    , _table_hostsbygroup(_downtimes, _comments, logger)
    , _table_servicegroups(logger)
    , _table_services(_downtimes, _comments, logger)
    , _table_servicesbygroup(_downtimes, _comments, logger)
    , _table_servicesbyhostgroup(_downtimes, _comments, logger)
    , _table_timeperiods(logger)
    , _table_contactgroups(logger)
    , _table_downtimes(_downtimes, _comments, logger)
    , _table_comments(_downtimes, _comments, logger)
    , _table_status(logger)
    , _table_log(&_log_cache, _downtimes, _comments, logger)
    , _table_statehistory(&_log_cache, _downtimes, _comments, logger)
    , _table_columns(logger)
    , _table_eventconsoleevents(_downtimes, _comments, logger)
    , _table_eventconsolehistory(_downtimes, _comments, logger)
    , _table_eventconsolestatus(logger)
    , _table_eventconsolereplication(logger)
    , _logger(logger) {
    addTable(&_table_columns);
    addTable(&_table_commands);
    addTable(&_table_comments);
    addTable(&_table_contactgroups);
    addTable(&_table_contacts);
    addTable(&_table_downtimes);
    addTable(&_table_hostgroups);
    addTable(&_table_hostsbygroup);
    addTable(&_table_hosts);
    addTable(&_table_log);
    addTable(&_table_servicegroups);
    addTable(&_table_servicesbygroup);
    addTable(&_table_servicesbyhostgroup);
    addTable(&_table_services);
    addTable(&_table_statehistory);
    addTable(&_table_status);
    addTable(&_table_timeperiods);
    addTable(&_table_eventconsoleevents);
    addTable(&_table_eventconsolehistory);
    addTable(&_table_eventconsolestatus);
    addTable(&_table_eventconsolereplication);
}

void Store::addTable(Table *table) {
    _tables.emplace(table->name(), table);
    _table_columns.addTable(table);
}

Table *Store::findTable(const string &name) {
    auto it = _tables.find(name);
    if (it == _tables.end()) {
        return nullptr;
    }
    return it->second;
}

void Store::registerDowntime(nebstruct_downtime_data *data) {
    _downtimes.registerDowntime(data);
}

void Store::registerComment(nebstruct_comment_data *data) {
    _comments.registerComment(data);
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
                OutputBuffer::ResponseCode::incomplete_request,
                "Client connection terminated while request still incomplete");
        }
        return false;
    }
    string l = input->nextLine();
    const char *line = l.c_str();
    Informational(_logger) << "Query: " << line;
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
        Informational(_logger) << "Forcing logfile rotation";
        rotate_log_file(time(nullptr));
        schedule_new_event(EVENT_LOG_ROTATION, 1, get_next_log_rotation_time(),
                           0, 0,
                           reinterpret_cast<void *>(get_next_log_rotation_time),
                           1, nullptr, nullptr, 0);
    } else {
        Warning(_logger) << "Invalid request '" << line << "'";
        output->setError(OutputBuffer::ResponseCode::invalid_request,
                         "Invalid request method");
    }
    return output->doKeepalive();
}

void Store::answerCommandRequest(const char *command) {
    if (answerLogwatchCommandRequest(command)) {
        return;
    }

    lock_guard<mutex> lg(_command_mutex);
#ifdef NAGIOS4
    process_external_command1((char *)command);
#else
    int buffer_items = -1;
    /* int ret = */
    submit_external_command(const_cast<char *>(command), &buffer_items);
#endif
}

bool Store::answerLogwatchCommandRequest(const char *command) {
    // Handle special command "[1462191638]
    // MK_LOGWATCH_ACKNOWLEDGE;host123;\var\log\syslog"
    if (strlen(command) >= 37 && command[0] == '[' && command[11] == ']' &&
        (strncmp(command + 13, "MK_LOGWATCH_ACKNOWLEDGE;", 24) == 0)) {
        const char *host_name_begin = command + 37;
        const char *host_name_end = strchr(host_name_begin, ';');
        if (host_name_end == nullptr) {
            return false;
        }
        std::string host_name(host_name_begin, host_name_end - host_name_begin);
        std::string file_name(host_name_end + 1);
        extern char g_mk_logwatch_path[];
        mk_logwatch_acknowledge(g_mk_logwatch_path, host_name, file_name);
        return true;
    }
    return false;
}

void Store::answerGetRequest(const list<string> &lines, OutputBuffer *output,
                             const char *tablename) {
    output->reset();

    if (tablename[0] == 0) {
        output->setError(OutputBuffer::ResponseCode::invalid_request,
                         "Invalid GET request, missing tablename");
        return;
    }

    Table *table = findTable(tablename);
    if (table == nullptr) {
        output->setError(
            OutputBuffer::ResponseCode::not_found,
            "Invalid GET request, no such table '" + string(tablename) + "'");
        return;
    }

    auto start = system_clock::now();
    Query(lines, table, g_data_encoding).process(output);
    auto elapsed = duration_cast<microseconds>(system_clock::now() - start);
    Informational(_logger) << "Time to process request: " << elapsed.count()
                           << "us. Size of answer: " << output->size()
                           << " bytes";
}
