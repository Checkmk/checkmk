// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Logger.h"

#include <cstddef>
#include <iostream>

#include "ChronoUtils.h"
#include "POSIXUtils.h"

// -----------------------------------------------------------------------------

std::ostream &operator<<(std::ostream &os, const LogLevel &c) {
    return os << static_cast<int>(c);
}

// -----------------------------------------------------------------------------

void SimpleFormatter::format(std::ostream &os, const LogRecord &record) {
    os << FormattedTimePoint(record.getTimePoint()) <<  //
        " [" << record.getLevel() << "] " << record.getMessage();
}

SharedStreamHandler::SharedStreamHandler(std::mutex &mutex, std::ostream &os)
    : _mutex(mutex), _os(os) {}

void SharedStreamHandler::publish(const LogRecord &record) {
    std::lock_guard<std::mutex> lg(_mutex);
    getFormatter()->format(_os, record);
    _os << std::endl;
}

StreamHandler::StreamHandler(std::ostream &os)
    : SharedStreamHandler(_mutex, os) {}

FileHandler::FileHandler(const std::string &filename) : StreamHandler(_os) {
    _os.open(filename, std::ofstream::app);
    if (!_os) {
        throw generic_error("could not open logfile " + filename);
    }
}

// -----------------------------------------------------------------------------

// static
Logger *Logger::getLogger(const std::string &name) {
    return LogManager::getLogManager()->getLogger(name);
}

bool Logger::isLoggable(LogLevel level) const { return level <= getLevel(); }

ConcreteLogger::ConcreteLogger(const std::string &name, Logger *parent)
    : _name(name)
    , _parent(parent)
    , _level(LogLevel::debug)
    , _handler(name.empty() ? nullptr : new StreamHandler(std::cerr))
    , _use_parent_handlers(true) {}

ConcreteLogger::~ConcreteLogger() { delete _handler; }

std::string ConcreteLogger::getName() const { return _name; }

Logger *ConcreteLogger::getParent() const { return _parent; }

LogLevel ConcreteLogger::getLevel() const { return _level; }

void ConcreteLogger::setLevel(LogLevel level) { _level = level; }

Handler *ConcreteLogger::getHandler() const { return _handler; }

void ConcreteLogger::setHandler(std::unique_ptr<Handler> handler) {
    std::scoped_lock l(_lock);
    delete _handler;
    _handler = handler.release();
}

bool ConcreteLogger::getUseParentHandlers() const {
    return _use_parent_handlers;
}
void ConcreteLogger::setUseParentHandlers(bool useParentHandlers) {
    _use_parent_handlers = useParentHandlers;
}

void ConcreteLogger::emitContext(std::ostream & /*unused*/) const {}

void ConcreteLogger::callHandler(const LogRecord &record) {
    std::scoped_lock l(_lock);
    if (Handler *handler = getHandler()) {
        handler->publish(record);
    }
}

void ConcreteLogger::log(const LogRecord &record) {
    if (!isLoggable(record.getLevel())) {
        return;
    }
    for (Logger *logger = this; logger != nullptr;
         logger = logger->getParent()) {
        logger->callHandler(record);
        if (!logger->getUseParentHandlers()) {
            break;
        }
    }
}

LoggerDecorator::LoggerDecorator(Logger *logger) : _logger(logger) {}

std::string LoggerDecorator::getName() const { return _logger->getName(); }

Logger *LoggerDecorator::getParent() const { return _logger->getParent(); }

LogLevel LoggerDecorator::getLevel() const { return _logger->getLevel(); }

void LoggerDecorator::setLevel(LogLevel level) { _logger->setLevel(level); }

Handler *LoggerDecorator::getHandler() const { return _logger->getHandler(); }

void LoggerDecorator::setHandler(std::unique_ptr<Handler> handler) {
    _logger->setHandler(std::move(handler));
}

void LoggerDecorator::callHandler(const LogRecord &record) {
    _logger->callHandler(record);
}

bool LoggerDecorator::getUseParentHandlers() const {
    return _logger->getUseParentHandlers();
}

void LoggerDecorator::setUseParentHandlers(bool useParentHandlers) {
    _logger->setUseParentHandlers(useParentHandlers);
}

void LoggerDecorator::emitContext(std::ostream &os) const {
    _logger->emitContext(os);
}

void LoggerDecorator::log(const LogRecord &record) { _logger->log(record); }

void ContextLogger::emitContext(std::ostream &os) const {
    _logger->emitContext(os);
    _context(os);
}

ThreadNameLogger::ThreadNameLogger(Logger *logger)
    : ContextLogger{logger, [](std::ostream &os) {
                        os << "[" << getThreadName() << "] ";
                    }} {}

ThreadNameLogger::ThreadNameLogger(const std::string &name)
    : ThreadNameLogger(Logger::getLogger(name)) {}

// -----------------------------------------------------------------------------

Logger *LogManager::getLogger(const std::string &name) {
    Logger *current = lookup("", nullptr);
    for (size_t pos = 0; pos <= name.size();) {
        size_t dot = name.find('.', pos);
        if (dot == std::string::npos) {
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

Logger *LogManager::lookup(const std::string &name, Logger *parent) {
    std::lock_guard<std::mutex> lg(_mutex);
    auto it = _known_loggers.find(name);
    if (it == _known_loggers.end()) {
        it = _known_loggers
                 .emplace(name, std::make_unique<ConcreteLogger>(name, parent))
                 .first;
    }
    return it->second.get();
}

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
LogManager LogManager::global_log_manager;

// -----------------------------------------------------------------------------

std::ostream &operator<<(std::ostream &os, const generic_error &ge) {
    return os << ge.what();
}
