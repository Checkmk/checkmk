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
#include <cstddef>
#include <iostream>
#include <utility>
#include "ChronoUtils.h"

using std::cerr;
using std::endl;
using std::lock_guard;
using std::make_unique;
using std::mutex;
using std::ostream;
using std::ostringstream;
using std::string;

ostream &operator<<(ostream &os, const LogLevel &c) {
    return os << static_cast<int>(c);
}

void SimpleFormatter::format(ostream &os, const LogRecord &record) {
    os << FormattedTimePoint(record.getTimePoint(), "%F %T ")  //
       << "[" << record.getLevel() << "] " << record.getMessage();
}

StreamHandler::StreamHandler(ostream &os) : _os(os) {}

void StreamHandler::publish(const LogRecord &record) {
    lock_guard<mutex> lg(_mutex);
    getFormatter()->format(_os, record);
    _os << endl;
}

FileHandler::FileHandler(const std::string &filename) : StreamHandler(_os) {
    _os.open(filename, std::ofstream::app);
    if (!_os) {
        throw generic_error("could not open logfile " + filename);
    }
}

Logger::Logger(string name, Logger *parent)
    : _name(move(name))
    , _parent(parent)
    , _level(LogLevel::debug)
    , _use_parent_handlers(true) {
    setHandler(make_unique<StreamHandler>(cerr));
}

Logger::~Logger() { delete getHandler(); }

// static
Logger *Logger::getLogger(const string &name) {
    return LogManager::getLogManager()->getLogger(name);
}

void Logger::log(const LogRecord &record) {
    if (!isLoggable(record.getLevel())) {
        return;
    }
    for (Logger *logger = this; logger != nullptr;
         logger = logger->getParent()) {
        if (Handler *handler = logger->getHandler()) {
            handler->publish(record);
        }
        if (!logger->getUseParentHandlers()) {
            break;
        }
    }
}

Logger *LogManager::getLogger(const string &name) {
    Logger *current = lookup("", nullptr);
    for (size_t pos = 0; pos <= name.size();) {
        size_t dot = name.find('.', pos);
        if (dot == string::npos) {
            dot = name.size();
        }
        if (dot != pos) {
            current = lookup(
                (current->getName().empty() ? "" : (current->getName() + ".")) +
                    name.substr(pos, dot - pos),
                current);
        }
        pos = dot + 1;
    }
    return current;
}

Logger *LogManager::lookup(const string &name, Logger *parent) {
    lock_guard<mutex> lg(_mutex);
    auto it = _known_loggers.find(name);
    if (it == _known_loggers.end()) {
        // Just because *we* are a friend of Logger doesn't mean that
        // make_unique is a friend, too, so we have to use a helper class.
        struct Helper : public Logger {
            Helper(const string &name, Logger *parent) : Logger(name, parent) {}
        };
        it = _known_loggers.emplace(name, make_unique<Helper>(name, parent))
                 .first;
    }
    return it->second.get();
}

LogManager LogManager::_global_log_manager;

ostream &operator<<(ostream &os, const generic_error &ge) {
    return os << ge.what();
}
