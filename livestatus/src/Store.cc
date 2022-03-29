// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Store.h"

#include <chrono>
#include <filesystem>
#include <memory>
#include <sstream>
#include <stdexcept>

#include "CrashReport.h"
#include "EventConsoleConnection.h"
#include "InputBuffer.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "OutputBuffer.h"
#include "Query.h"
#include "StringUtils.h"
#include "mk_logwatch.h"
#include "nagios.h"

Store::Store(MonitoringCore *mc)
    : _mc(mc)
    , _log_cache(mc)
    , _table_columns(mc)
    , _table_commands(mc)
    , _table_comments(mc)
    , _table_contactgroups(mc)
    , _table_contacts(mc)
    , _table_crash_reports(mc)
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
    , _table_timeperiods(mc)
    , _table_dummy(mc) {
    addTable(_table_columns);
    addTable(_table_commands);
    addTable(_table_comments);
    addTable(_table_contactgroups);
    addTable(_table_contacts);
    addTable(_table_crash_reports);
    addTable(_table_downtimes);
    addTable(_table_hostgroups);
    addTable(_table_hostsbygroup);
    addTable(_table_hosts);
    addTable(_table_log);
    addTable(_table_servicegroups);
    addTable(_table_servicesbygroup);
    addTable(_table_servicesbyhostgroup);
    addTable(_table_services);
    addTable(_table_statehistory);
    addTable(_table_status);
    addTable(_table_timeperiods);
    addTable(_table_eventconsoleevents);
    addTable(_table_eventconsolehistory);
    addTable(_table_eventconsolestatus);
    addTable(_table_eventconsolereplication);
    addTable(_table_eventconsolerules);
}

void Store::addTable(Table &table) {
    _tables.emplace(table.name(), &table);
    _table_columns.addTable(table);
}

Table &Store::findTable(OutputBuffer &output, const std::string &name) {
    // NOTE: Even with an invalid table name we continue, so we can parse
    // headers, especially ResponseHeader.
    if (name.empty()) {
        output.setError(OutputBuffer::ResponseCode::invalid_request,
                        "Invalid GET request, missing table name");
        return _table_dummy;
    }
    auto it = _tables.find(name);
    if (it == _tables.end()) {
        output.setError(OutputBuffer::ResponseCode::not_found,
                        "Invalid GET request, no such table '" + name + "'");
        return _table_dummy;
    }
    return *it->second;
}

namespace {
std::list<std::string> getLines(InputBuffer &input) {
    std::list<std::string> lines;
    while (!input.empty()) {
        lines.push_back(input.nextLine());
        if (lines.back().empty()) {
            break;
        }
    }
    return lines;
}
}  // namespace

void Store::logRequest(const std::string &line,
                       const std::list<std::string> &lines) const {
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

Store::ExternalCommand::ExternalCommand(const std::string &str) {
    constexpr int timestamp_len = 10;
    constexpr int prefix_len = timestamp_len + 3;
    if (str.size() <= prefix_len || str[0] != '[' ||
        str[prefix_len - 2] != ']' || str[prefix_len - 1] != ' ') {
        throw std::invalid_argument("malformed timestamp in command '" + str +
                                    "'");
    }
    auto semi = str.find(';', prefix_len);
    _prefix = str.substr(0, prefix_len);
    _name = str.substr(prefix_len, semi - prefix_len);
    _arguments = semi == std::string::npos ? "" : str.substr(semi);
}

Store::ExternalCommand Store::ExternalCommand::withName(
    const std::string &name) const {
    return {_prefix, name, _arguments};
}

std::string Store::ExternalCommand::str() const {
    return _prefix + _name + _arguments;
}

std::vector<std::string> Store::ExternalCommand::args() const {
    if (_arguments.empty()) {
        return {};
    }
    return mk::split(_arguments.substr(1), ';');
}

bool Store::answerRequest(InputBuffer &input, OutputBuffer &output) {
    // Precondition: output has been reset
    InputBuffer::Result res = input.readRequest();
    if (res != InputBuffer::Result::request_read) {
        if (res != InputBuffer::Result::eof) {
            std::ostringstream os;
            os << "client connection terminated: " << res;
            output.setError(OutputBuffer::ResponseCode::incomplete_request,
                            os.str());
        }
        return false;
    }
    std::string line = input.nextLine();
    if (mk::starts_with(line, "GET ")) {
        auto lines = getLines(input);
        logRequest(line, lines);
        return answerGetRequest(lines, output, mk::lstrip(line.substr(4)));
    }
    if (mk::starts_with(line, "GET")) {
        // only to get error message
        auto lines = getLines(input);
        logRequest(line, lines);
        return answerGetRequest(lines, output, "");
    }
    if (mk::starts_with(line, "COMMAND ")) {
        logRequest(line, {});
        try {
            answerCommandRequest(ExternalCommand(mk::lstrip(line.substr(8))));
        } catch (const std::invalid_argument &err) {
            Warning(logger()) << err.what();
        }
        return true;
    }
    if (mk::starts_with(line, "LOGROTATE")) {
        logRequest(line, {});
        Informational(logger()) << "Forcing logfile rotation";
        rotate_log_file(std::chrono::system_clock::to_time_t(
            std::chrono::system_clock::now()));
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

void Store::answerCommandRequest(const ExternalCommand &command) {
    if (command.name() == "MK_LOGWATCH_ACKNOWLEDGE") {
        answerCommandMkLogwatchAcknowledge(command);
        return;
    }
    if (command.name() == "DEL_CRASH_REPORT") {
        answerCommandDelCrashReport(command);
        return;
    }
    if (mk::starts_with(command.name(), "EC_")) {
        answerCommandEventConsole(command);
        return;
    }
    // Nagios doesn't have a LOG command, so we map it to the custom command
    // _LOG, which we implement for ourselves.
    answerCommandNagios(command.name() == "LOG" ? command.withName("_LOG")
                                                : command);
}

void Store::answerCommandMkLogwatchAcknowledge(const ExternalCommand &command) {
    // COMMAND [1462191638] MK_LOGWATCH_ACKNOWLEDGE;host123;\var\log\syslog
    auto args = command.args();
    if (args.size() != 2) {
        Warning(logger()) << "MK_LOGWATCH_ACKNOWLEDGE expects 2 arguments";
        return;
    }
    mk_logwatch_acknowledge(logger(), _mc->mkLogwatchPath(), args[0], args[1]);
}

void Store::answerCommandDelCrashReport(const ExternalCommand &command) {
    auto args = command.args();
    if (args.size() != 1) {
        Warning(logger()) << "DEL_CRASH_REPORT expects 1 argument";
        return;
    }
    mk::crash_report::delete_id(_mc->crashReportPath(), args[0], logger());
}

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(Logger *logger, std::string path, std::string command)
        : EventConsoleConnection(logger, move(path))
        , command_(std::move(command)) {}

private:
    void sendRequest(std::ostream &os) override { os << command_; }
    void receiveReply(std::istream & /*is*/) override {}
    std::string command_;
};
}  // namespace

void Store::answerCommandEventConsole(const ExternalCommand &command) {
    if (!_mc->mkeventdEnabled()) {
        Notice(logger()) << "event console disabled, ignoring command '"
                         << command.str() << "'";
        return;
    }
    try {
        ECTableConnection(
            logger(), _mc->mkeventdSocketPath(),
            "COMMAND " + command.name().substr(3) + command.arguments())
            .run();
    } catch (const std::runtime_error &err) {
        Alert(logger()) << err.what();
    }
}

void Store::answerCommandNagios(const ExternalCommand &command) {
    std::lock_guard<std::mutex> lg(_command_mutex);
    nagios_compat_submit_external_command(command.str().c_str());
}

bool Store::answerGetRequest(const std::list<std::string> &lines,
                             OutputBuffer &output,
                             const std::string &tablename) {
    return Query{lines,
                 findTable(output, tablename),
                 _mc->dataEncoding(),
                 _mc->maxResponseSize(),
                 _mc->serviceAuthorization(),
                 _mc->groupAuthorization(),
                 output,
                 logger()}
        .process();
}

Logger *Store::logger() const { return _mc->loggerLivestatus(); }

size_t Store::numCachedLogMessages() {
    return _log_cache.numCachedLogMessages();
}
