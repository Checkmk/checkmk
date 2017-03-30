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
using std::unique_ptr;

// -----------------------------------------------------------------------------

ostream &operator<<(ostream &os, const LogLevel &c) {
    return os << static_cast<int>(c);
}

// -----------------------------------------------------------------------------

void SimpleFormatter::format(ostream &os, const LogRecord &record) {
    os << FormattedTimePoint(record.getTimePoint()) <<  //
        " [" << record.getLevel() << "] " << record.getMessage();
}

SharedStreamHandler::SharedStreamHandler(mutex &mutex, ostream &os)
    : _mutex(mutex), _os(os) {}

void SharedStreamHandler::publish(const LogRecord &record) {
    lock_guard<mutex> lg(_mutex);
    getFormatter()->format(_os, record);
    _os << endl;
}

StreamHandler::StreamHandler(ostream &os) : SharedStreamHandler(_mutex, os) {}

FileHandler::FileHandler(const string &filename) : StreamHandler(_os) {
    _os.open(filename, std::ofstream::app);
    if (!_os) {
        throw generic_error("could not open logfile " + filename);
    }
}

// -----------------------------------------------------------------------------

// static
Logger *Logger::getLogger(const string &name) {
    return LogManager::getLogManager()->getLogger(name);
}

bool Logger::isLoggable(LogLevel level) const { return level <= getLevel(); }

ConcreteLogger::ConcreteLogger(const string &name, Logger *parent)
    : _name(name)
    , _parent(parent)
    , _level(LogLevel::debug)
    , _handler(name.empty() ? nullptr : new StreamHandler(cerr))
    , _use_parent_handlers(true) {}

ConcreteLogger::~ConcreteLogger() { setHandler(unique_ptr<Handler>()); }

string ConcreteLogger::getName() const { return _name; }

Logger *ConcreteLogger::getParent() const { return _parent; }

LogLevel ConcreteLogger::getLevel() const { return _level; }

void ConcreteLogger::setLevel(LogLevel level) { _level = level; }

Handler *ConcreteLogger::getHandler() const { return _handler; }

void ConcreteLogger::setHandler(unique_ptr<Handler> handler) {
    delete _handler;
    _handler = handler.release();
}

bool ConcreteLogger::getUseParentHandlers() const {
    return _use_parent_handlers;
}
void ConcreteLogger::setUseParentHandlers(bool useParentHandlers) {
    _use_parent_handlers = useParentHandlers;
}

void ConcreteLogger::emitContext(ostream & /*unused*/) const {}

void ConcreteLogger::log(const LogRecord &record) {
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

LoggerDecorator::LoggerDecorator(Logger *logger) : _logger(logger) {}

string LoggerDecorator::getName() const { return _logger->getName(); }

Logger *LoggerDecorator::getParent() const { return _logger->getParent(); }

LogLevel LoggerDecorator::getLevel() const { return _logger->getLevel(); }

void LoggerDecorator::setLevel(LogLevel level) { _logger->setLevel(level); }

Handler *LoggerDecorator::getHandler() const { return _logger->getHandler(); }

void LoggerDecorator::setHandler(unique_ptr<Handler> handler) {
    _logger->setHandler(move(handler));
}

bool LoggerDecorator::getUseParentHandlers() const {
    return _logger->getUseParentHandlers();
}

void LoggerDecorator::setUseParentHandlers(bool useParentHandlers) {
    _logger->setUseParentHandlers(useParentHandlers);
}

void LoggerDecorator::emitContext(ostream &os) const {
    _logger->emitContext(os);
}

void LoggerDecorator::log(const LogRecord &record) { _logger->log(record); }

void ContextLogger::emitContext(ostream &os) const {
    _logger->emitContext(os);
    _context(os);
}

// -----------------------------------------------------------------------------

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
        it = _known_loggers
                 .emplace(name, make_unique<ConcreteLogger>(name, parent))
                 .first;
    }
    return it->second.get();
}

LogManager LogManager::_global_log_manager;

// -----------------------------------------------------------------------------

ostream &operator<<(ostream &os, const generic_error &ge) {
    return os << ge.what();
}
