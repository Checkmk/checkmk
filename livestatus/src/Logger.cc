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

#include "Logger.h"
#include <algorithm>
#include <iostream>
#include "ChronoUtils.h"

using std::cout;
using std::lock_guard;
using std::make_unique;
using std::mutex;
using std::ostream;
using std::ostringstream;
using std::string;
using std::unique_ptr;

ostream &operator<<(ostream &os, const LogLevel &c) {
    return os << static_cast<int>(c);
}

string SimpleFormatter::format(const LogRecord &record) const {
    ostringstream os;
    os << FormattedTimePoint(record.getTimePoint(), "%F %T ")  //
       << "[" << record.getLevel() << "] " << record.getMessage();
    return os.str();
}

Handler::Handler() { setFormatter(make_unique<SimpleFormatter>()); }

Formatter *Handler::getFormatter() {
    lock_guard<mutex> lg(_mutex);
    return _formatter.get();
}

void Handler::setFormatter(unique_ptr<Formatter> formatter) {
    lock_guard<mutex> lg(_mutex);
    _formatter = move(formatter);
}

StreamHandler::StreamHandler(ostream &os) : _os(os) {}

void StreamHandler::publish(const LogRecord &record) {
    lock_guard<mutex> lg(_mutex);
    _os << getFormatter()->format(record) << std::endl;
}

FileHandler::FileHandler(const std::string &filename) : StreamHandler(_os) {
    _os.open(filename, std::ofstream::app);
    if (!_os) {
        throw generic_error("could not open logfile " + filename);
    }
}

Logger::Logger()
    : _level(LogLevel::debug), _handler(make_unique<StreamHandler>(cout)) {}

LogLevel Logger::getLevel() {
    lock_guard<mutex> lg(_mutex);
    return _level;
}

// cppcheck-suppress unusedFunction
void Logger::setLevel(LogLevel level) {
    lock_guard<mutex> lg(_mutex);
    _level = level;
}

// cppcheck-suppress unusedFunction
Handler *Logger::getHandler() {
    lock_guard<mutex> lg(_mutex);
    return _handler.get();
}

void Logger::setHandler(std::unique_ptr<Handler> handler) {
    lock_guard<mutex> lg(_mutex);
    _handler = std::move(handler);
}

// cppcheck-suppress unusedFunction
bool Logger::isLoggable(LogLevel level) { return level <= getLevel(); }

void Logger::log(const LogRecord &record) {
    lock_guard<mutex> lg(_mutex);
    if (record.getLevel() <= _level && _handler) {
        _handler->publish(record);
    }
}

Logger Logger::_global_logger;
