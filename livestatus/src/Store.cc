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
#include "DowntimeOrComment.h"  // IWYU pragma: keep
#include "EventConsoleConnection.h"
#include "InputBuffer.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "OutputBuffer.h"
#include "Query.h"
#include "StringUtils.h"
#include "Table.h"
#include "mk_logwatch.h"

using mk::lstrip;
using mk::split;
using mk::starts_with;
using std::list;
using std::lock_guard;
using std::mutex;
using std::string;

Store::Store(MonitoringCore *mc)
    : _mc(mc)
    , _log_cache(mc, mc->maxCachedMessages())
    , _table_columns(mc)
    , _table_commands(mc)
    , _table_comments(mc)
    , _table_contactgroups(mc)
    , _table_contacts(mc)
    , _table_downtimes(mc)
    , _table_eventconsoleevents(mc)
    , _table_eventconsolehistory(mc)
    , _table_eventconsolereplication(mc)
    , _table_eventconsolerules(mc)
    , _table_eventconsolestatus(mc)
    , _table_hostgroups(mc)
    , _table_hosts(mc)
    , _table_hostsbygroup(mc)
    , _table_log(mc, &_log_cache)
    , _table_servicegroups(mc)
    , _table_services(mc)
    , _table_servicesbygroup(mc)
    , _table_servicesbyhostgroup(mc)
    , _table_statehistory(mc, &_log_cache)
    , _table_status(mc)
    , _table_timeperiods(mc) {
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
    addTable(&_table_eventconsolerules);
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
    Informational log(logger());
    log << "request: " << line;
    if (logger()->isLoggable(LogLevel::debug)) {
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
    string line = input.nextLine();
    if (starts_with(line, "GET ")) {
        auto lines = getLines(input);
        logRequest(line, lines);
        return answerGetRequest(lines, output, lstrip(line.substr(4)));
    }
    if (starts_with(line, "GET")) {
        // only to get error message
        auto lines = getLines(input);
        logRequest(line, lines);
        return answerGetRequest(lines, output, "");
    }
    if (starts_with(line, "COMMAND ")) {
        logRequest(line, {});
        answerCommandRequest(lstrip(line.substr(8)).c_str());
        return true;
    }
    if (starts_with(line, "LOGROTATE")) {
        logRequest(line, {});
        Informational(logger()) << "Forcing logfile rotation";
        rotate_log_file(time(nullptr));
        schedule_new_event(EVENT_LOG_ROTATION, 1, get_next_log_rotation_time(),
                           0, 0,
                           reinterpret_cast<void *>(get_next_log_rotation_time),
                           1, nullptr, nullptr, 0);
        return false;
    }
    logRequest(line, {});
    Warning(logger()) << "Invalid request '" << line << "'";
    output.setError(OutputBuffer::ResponseCode::invalid_request,
                    "Invalid request method");
    return false;
}

void Store::answerCommandRequest(const char *command) {
    int len = strlen(command);
    if (len < 14 || command[0] != '[' || command[11] != ']' ||
        command[12] != ' ') {
        Warning(logger()) << "Ignoring malformed command '" << command << "'";
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
        : EventConsoleConnection(logger, move(path)), _command(move(command)) {}

private:
    void sendRequest(std::ostream &os) override { os << _command; }
    void receiveReply(std::istream & /*is*/) override {}
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
            Warning(logger()) << "MK_LOGWATCH_ACKNOWLEDGE expects 2 arguments";
        } else {
            mk_logwatch_acknowledge(logger(), _mc->mkLogwatchPath(), parts[1],
                                    parts[2]);
        }
        return true;
    }

    if (starts_with(command_name, "EC_")) {
        if (!_mc->mkeventdEnabled()) {
            Notice(logger()) << "event console disabled, ignoring command '"
                             << command << "'";
        } else {
            ECTableConnection(logger(), _mc->mkeventdSocketPath(),
                              "COMMAND " + command.substr(3))
                .run();
        }
        return true;
    }

    return false;
}

bool Store::answerGetRequest(const list<string> &lines, OutputBuffer &output,
                             const string &tablename) {
    if (tablename.empty()) {
        output.setError(OutputBuffer::ResponseCode::invalid_request,
                        "Invalid GET request, missing tablename");
        return false;
    }

    Table *table = findTable(tablename);
    if (table == nullptr) {
        output.setError(
            OutputBuffer::ResponseCode::not_found,
            "Invalid GET request, no such table '" + string(tablename) + "'");
        return false;
    }

    return Query(lines, table, _mc->dataEncoding(), _mc->maxResponseSize(),
                 output)
        .process();
}

Logger *Store::logger() const { return _mc->loggerLivestatus(); }
