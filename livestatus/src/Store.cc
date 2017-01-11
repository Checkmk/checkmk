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

// Some IWYU versions don't like it, some versions require it... :-P
// IWYU pragma: no_include <memory>
#include "Store.h"
#include <cstring>
#include <ctime>
#include <ostream>
#include <utility>
#include <vector>
#include "EventConsoleConnection.h"
#include "InputBuffer.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "OutputBuffer.h"
#include "Query.h"
#include "StringUtils.h"
#include "Table.h"
#include "data_encoding.h"
#include "mk_logwatch.h"
#include "strutil.h"

extern Encoding g_data_encoding;
extern unsigned long g_max_cached_messages;

using mk::split;
using mk::starts_with;
using std::list;
using std::lock_guard;
using std::mutex;
using std::string;

Store::Store(MonitoringCore *core)
    : _core(core)
    , _logger(core->loggerLivestatus())
    , _log_cache(_logger, _commands_holder, g_max_cached_messages)
    , _table_contacts(_logger)
    , _table_commands(_commands_holder, _logger)
    , _table_hostgroups(_logger)
    , _table_hosts(_downtimes, _comments, core)
    , _table_hostsbygroup(_downtimes, _comments, core)
    , _table_servicegroups(_logger)
    , _table_services(_downtimes, _comments, core)
    , _table_servicesbygroup(_downtimes, _comments, core)
    , _table_servicesbyhostgroup(_downtimes, _comments, core)
    , _table_timeperiods(_logger)
    , _table_contactgroups(_core)
    , _table_downtimes(_downtimes, _comments, core)
    , _table_comments(_downtimes, _comments, core)
    , _table_status(_logger)
    , _table_log(&_log_cache, _downtimes, _comments, core)
    , _table_statehistory(&_log_cache, _downtimes, _comments, core)
    , _table_columns(_logger)
    , _table_eventconsoleevents(core, _downtimes, _comments)
    , _table_eventconsolehistory(core, _downtimes, _comments)
    , _table_eventconsolestatus(core)
    , _table_eventconsolereplication(core) {
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
list<string> getLines(InputBuffer &input) {
    list<string> lines;
    while (!input.empty()) {
        lines.push_back(input.nextLine());
        if (lines.back().empty()) {
            break;
        }
    }
    return lines;
}
}  // namespace

void Store::logRequest(const string &line, const list<string> &lines) {
    Informational log(_logger);
    log << "request: " << line;
    if (_logger->isLoggable(LogLevel::debug)) {
        for (const auto &l : lines) {
            log << R"(\n)" << l;
        }
    } else {
        size_t s = lines.size();
        if (s > 0) {
            log << R"(\n{)" << s << (s == 1 ? " line follows" : " lines follow")
                << "...}";
        }
    }
}

bool Store::answerRequest(InputBuffer &input, OutputBuffer &output) {
    // Precondition: output has been reset
    InputBuffer::Result res = input.readRequest();
    if (res != InputBuffer::Result::request_read) {
        if (res != InputBuffer::Result::eof) {
            output.setError(
                OutputBuffer::ResponseCode::incomplete_request,
                "Client connection terminated while request still incomplete");
        }
        return false;
    }
    string l = input.nextLine();
    const char *line = l.c_str();
    if (strncmp(line, "GET ", 4) == 0) {
        auto lines = getLines(input);
        logRequest(l, lines);
        answerGetRequest(lines, output, lstrip(const_cast<char *>(line) + 4));
    } else if (strcmp(line, "GET") == 0) {
        // only to get error message
        auto lines = getLines(input);
        logRequest(l, lines);
        answerGetRequest(lines, output, "");
    } else if (strncmp(line, "COMMAND ", 8) == 0) {
        logRequest(l, {});
        answerCommandRequest(lstrip(const_cast<char *>(line) + 8));
        output.setDoKeepalive(true);
    } else if (strncmp(line, "LOGROTATE", 9) == 0) {
        logRequest(l, {});
        Informational(_logger) << "Forcing logfile rotation";
        rotate_log_file(time(nullptr));
        schedule_new_event(EVENT_LOG_ROTATION, 1, get_next_log_rotation_time(),
                           0, 0,
                           reinterpret_cast<void *>(get_next_log_rotation_time),
                           1, nullptr, nullptr, 0);
    } else {
        logRequest(l, {});
        Warning(_logger) << "Invalid request '" << l << "'";
        output.setError(OutputBuffer::ResponseCode::invalid_request,
                        "Invalid request method");
    }
    return output.doKeepalive();
}

void Store::answerCommandRequest(const char *command) {
    int len = strlen(command);
    if (len < 14 || command[0] != '[' || command[11] != ']' ||
        command[12] != ' ') {
        Warning(_logger) << "Ignoring malformed command '" << command << "'";
        return;
    }

    if (handleCommand(command + 13)) {
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

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(Logger *logger, string path, string command)
        : EventConsoleConnection(logger, path), _command(move(command)) {}

private:
    void sendRequest(std::ostream &os) override { os << _command; }
    bool receiveReply() override { return true; }
    string _command;
};
}  // namespace

bool Store::handleCommand(const string &command) {
    auto parts = split(command, ';');
    if (parts.empty()) {
        return false;
    }
    string command_name = parts[0];

    if (command_name == "MK_LOGWATCH_ACKNOWLEDGE") {
        // COMMAND [1462191638] MK_LOGWATCH_ACKNOWLEDGE;host123;\var\log\syslog
        if (parts.size() != 3) {
            Warning(_logger) << "MK_LOGWATCH_ACKNOWLEDGE expects 2 arguments";
            return false;
        }
        extern char g_mk_logwatch_path[];
        mk_logwatch_acknowledge(_logger, g_mk_logwatch_path, parts[1],
                                parts[2]);
        return true;
    }

    if (starts_with(command_name, "EC_")) {
        if (parts.size() != 1) {
            Warning(_logger) << command_name << "expects 0 arguments";
            return false;
        }
        if (_core->mkeventdEnabled()) {
            ECTableConnection(_logger, _core->mkeventdSocketPath(),
                              "COMMAND " + command_name.substr(3))
                .run();
        } else {
            Notice(_logger) << "event console disabled, ignoring command '"
                            << command << "'";
        }
        return true;
    }

    return false;
}

void Store::answerGetRequest(const list<string> &lines, OutputBuffer &output,
                             const string &tablename) {
    if (tablename.empty()) {
        output.setError(OutputBuffer::ResponseCode::invalid_request,
                        "Invalid GET request, missing tablename");
        return;
    }

    Table *table = findTable(tablename);
    if (table == nullptr) {
        output.setError(
            OutputBuffer::ResponseCode::not_found,
            "Invalid GET request, no such table '" + string(tablename) + "'");
        return;
    }

    Query(lines, table, g_data_encoding, output).process();
}
