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

#ifndef Logger_h
#define Logger_h

#include "config.h"  // IWYU pragma: keep
#include <atomic>
#include <cerrno>
#include <chrono>
#include <fstream>  // IWYU pragma: keep
#include <functional>
#include <memory>
#include <mutex>
#include <sstream>  // IWYU pragma: keep
#include <string>
#include <system_error>
#include <unordered_map>

// -----------------------------------------------------------------------------

// values must be in sync with config
enum class LogLevel {
    emergency = 0,
    alert = 1,
    critical = 2,
    error = 3,
    warning = 4,
    notice = 5,
    informational = 6,
    debug = 7
};

std::ostream &operator<<(std::ostream &os, const LogLevel &c);

// -----------------------------------------------------------------------------

class LogRecord {
public:
    LogRecord(LogLevel level, const std::string &message)
        : _level(level)
        , _message(message)
        , _time_point(std::chrono::system_clock::now()) {}
    virtual ~LogRecord() {}

    LogLevel getLevel() const { return _level; }
    void setLevel(LogLevel level) { _level = level; }

    std::string getMessage() const { return _message; }
    void setMessage(const std::string &message) { _message = message; }

    std::chrono::system_clock::time_point getTimePoint() const {
        return _time_point;
    }
    void setTimePoint(std::chrono::system_clock::time_point time_point) {
        _time_point = time_point;
    }

private:
    LogLevel _level;
    std::string _message;
    std::chrono::system_clock::time_point _time_point;
};

// -----------------------------------------------------------------------------

class Formatter {
public:
    virtual ~Formatter() = default;
    virtual void format(std::ostream &os, const LogRecord &record) = 0;
};

class SimpleFormatter : public Formatter {
    friend class Handler;
    void format(std::ostream &os, const LogRecord &record) override;
};

// -----------------------------------------------------------------------------

class Handler {
public:
    virtual ~Handler() { delete getFormatter(); }
    virtual void publish(const LogRecord &record) = 0;

    Formatter *getFormatter() const { return _formatter; }
    void setFormatter(std::unique_ptr<Formatter> formatter) {
        _formatter = formatter.release();
    }

protected:
    Handler() { setFormatter(std::make_unique<SimpleFormatter>()); }

private:
    std::atomic<Formatter *> _formatter;
};

class StreamHandler : public Handler {
public:
    explicit StreamHandler(std::ostream &os);

private:
    std::mutex _mutex;
    std::ostream &_os;

    void publish(const LogRecord &record) override;
};

class FileHandler : public StreamHandler {
public:
    explicit FileHandler(const std::string &filename);

private:
    std::ofstream _os;
};

// -----------------------------------------------------------------------------

class Logger {
public:
    static Logger *getLogger(const std::string &name);

    ~Logger();

    std::string getName() const { return _name; }

    Logger *getParent() const { return _parent; }

    LogLevel getLevel() const { return _level; }
    void setLevel(LogLevel level) { _level = level; }

    Handler *getHandler() const { return _handler; }
    void setHandler(std::unique_ptr<Handler> handler) {
        _handler = handler.release();
    }

    bool getUseParentHandlers() const { return _use_parent_handlers; }
    void setUseParentHandlers(bool useParentHandlers) {
        _use_parent_handlers = useParentHandlers;
    }

    bool isLoggable(LogLevel level) { return level <= getLevel(); }
    void log(const LogRecord &record);

private:
    static Logger _global_logger;

    const std::string _name;
    Logger *const _parent;
    std::atomic<LogLevel> _level;
    std::atomic<Handler *> _handler;
    std::atomic<bool> _use_parent_handlers;

    Logger(std::string name, Logger *parent);
    friend class LogManager;
};

// -----------------------------------------------------------------------------

class LogManager {
public:
    static LogManager *getLogManager() { return &_global_log_manager; }
    Logger *getLogger(const std::string &name);

private:
    static LogManager _global_log_manager;

    std::mutex _mutex;
    std::unordered_map<std::string, std::unique_ptr<Logger>> _known_loggers;

    Logger *lookup(const std::string &name, Logger *parent);
};

// -----------------------------------------------------------------------------

class LogStream {
public:
    LogStream(Logger *logger, LogLevel level)
        : _logger(logger), _level(level) {}
    virtual ~LogStream() {
        if (_logger->isLoggable(_level)) {  // the test is just an optimization
            _logger->log(LogRecord(_level, _os.str()));
        }
    }

    template <typename T>
    std::ostream &operator<<(const T &t) {
        // the test is just an optimization
        return _logger->isLoggable(_level) ? (_os << t) : _os;
    }

protected:
    Logger *const _logger;
    const LogLevel _level;
    std::ostringstream _os;
};

// -----------------------------------------------------------------------------

class LoggerAdapter {
public:
    LoggerAdapter(Logger *l, const std::function<void(std::ostream &)> &p)
        : logger(l), prefix(p) {}

    Logger *const logger;
    const std::function<void(std::ostream &)> prefix;
};

// -----------------------------------------------------------------------------

struct Emergency : public LogStream {
    explicit Emergency(Logger *logger)
        : LogStream(logger, LogLevel::emergency) {}
    explicit Emergency(LoggerAdapter &adapter)
        : LogStream(adapter.logger, LogLevel::emergency) {
        adapter.prefix(_os);
    }
};

struct Alert : public LogStream {
    explicit Alert(Logger *logger) : LogStream(logger, LogLevel::alert) {}
    explicit Alert(LoggerAdapter &adapter)
        : LogStream(adapter.logger, LogLevel::alert) {}
};

struct Critical : public LogStream {
    explicit Critical(Logger *logger) : LogStream(logger, LogLevel::critical) {}
    explicit Critical(LoggerAdapter &adapter)
        : LogStream(adapter.logger, LogLevel::critical) {
        adapter.prefix(_os);
    }
};

struct Error : public LogStream {
    explicit Error(Logger *logger) : LogStream(logger, LogLevel::error) {}
    explicit Error(LoggerAdapter &adapter)
        : LogStream(adapter.logger, LogLevel::error) {
        adapter.prefix(_os);
    }
};

struct Warning : public LogStream {
    explicit Warning(Logger *logger) : LogStream(logger, LogLevel::warning) {}
    explicit Warning(LoggerAdapter &adapter)
        : LogStream(adapter.logger, LogLevel::warning) {
        adapter.prefix(_os);
    }
};

struct Notice : public LogStream {
    explicit Notice(Logger *logger) : LogStream(logger, LogLevel::notice) {}
    explicit Notice(LoggerAdapter &adapter)
        : LogStream(adapter.logger, LogLevel::notice) {
        adapter.prefix(_os);
    }
};

struct Informational : public LogStream {
    explicit Informational(Logger *logger)
        : LogStream(logger, LogLevel::informational) {}
    explicit Informational(LoggerAdapter &adapter)
        : LogStream(adapter.logger, LogLevel::informational) {
        adapter.prefix(_os);
    }
};

struct Debug : public LogStream {
    explicit Debug(Logger *logger) : LogStream(logger, LogLevel::debug) {}
    explicit Debug(LoggerAdapter &adapter)
        : LogStream(adapter.logger, LogLevel::debug) {
        adapter.prefix(_os);
    }
};

// -----------------------------------------------------------------------------

class generic_error : public std::system_error {
public:
    generic_error() : std::system_error(errno, std::generic_category()) {}

    explicit generic_error(const char *what_arg)
        : std::system_error(errno, std::generic_category(), what_arg) {}

    explicit generic_error(const std::string &what_arg)
        : std::system_error(errno, std::generic_category(), what_arg) {}
};

std::ostream &operator<<(std::ostream &os, const generic_error &ge);

#endif  // Logger_h
