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
#include <fstream>
#include <functional>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <system_error>
#include <unordered_map>
#include <utility>

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
    LogRecord(LogLevel level, std::string message)
        : _level(level)
        , _message(std::move(message))
        , _time_point(std::chrono::system_clock::now()) {}
    virtual ~LogRecord() = default;

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
    virtual ~Handler() { setFormatter(std::unique_ptr<Formatter>()); }
    virtual void publish(const LogRecord &record) = 0;

    Formatter *getFormatter() const { return _formatter; }
    void setFormatter(std::unique_ptr<Formatter> formatter) {
        delete _formatter;
        _formatter = formatter.release();
    }

protected:
    Handler() : _formatter(new SimpleFormatter()) {}

private:
    std::atomic<Formatter *> _formatter;
};

class SharedStreamHandler : public Handler {
public:
    SharedStreamHandler(std::mutex &mutex, std::ostream &os);

private:
    // The mutex protects the _os.
    std::mutex &_mutex;
    std::ostream &_os;

    void publish(const LogRecord &record) override;
};

class StreamHandler : public SharedStreamHandler {
public:
    explicit StreamHandler(std::ostream &os);

private:
    // The mutex protects the output stream, see SharedStreamHandler.
    std::mutex _mutex;
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

    virtual ~Logger() = default;

    bool isLoggable(LogLevel level) const;

    virtual std::string getName() const = 0;

    virtual Logger *getParent() const = 0;

    virtual LogLevel getLevel() const = 0;
    virtual void setLevel(LogLevel level) = 0;

    virtual Handler *getHandler() const = 0;
    virtual void setHandler(std::unique_ptr<Handler> handler) = 0;

    virtual bool getUseParentHandlers() const = 0;
    virtual void setUseParentHandlers(bool useParentHandlers) = 0;

    virtual void emitContext(std::ostream &os) const = 0;

    virtual void log(const LogRecord &record) = 0;
};

class ConcreteLogger : public Logger {
public:
    ConcreteLogger(const std::string &name, Logger *parent);
    ~ConcreteLogger() override;

    std::string getName() const override;

    Logger *getParent() const override;

    LogLevel getLevel() const override;
    void setLevel(LogLevel level) override;

    Handler *getHandler() const override;
    void setHandler(std::unique_ptr<Handler> handler) override;

    bool getUseParentHandlers() const override;
    void setUseParentHandlers(bool useParentHandlers) override;

    void emitContext(std::ostream &os) const override;

    void log(const LogRecord &record) override;

private:
    const std::string _name;
    Logger *const _parent;
    std::atomic<LogLevel> _level;
    std::atomic<Handler *> _handler;
    std::atomic<bool> _use_parent_handlers;
};

class LoggerDecorator : public Logger {
public:
    explicit LoggerDecorator(Logger *logger);

    std::string getName() const override;

    Logger *getParent() const override;

    LogLevel getLevel() const override;
    void setLevel(LogLevel level) override;

    Handler *getHandler() const override;
    void setHandler(std::unique_ptr<Handler> handler) override;

    bool getUseParentHandlers() const override;
    void setUseParentHandlers(bool useParentHandlers) override;

    void emitContext(std::ostream &os) const override;

    void log(const LogRecord &record) override;

protected:
    Logger *const _logger;
};

class ContextLogger : public LoggerDecorator {
public:
    using ContextEmitter = std::function<void(std::ostream &)>;

    ContextLogger(Logger *logger, ContextEmitter context)
        : LoggerDecorator(logger), _context(std::move(context)) {}

    void emitContext(std::ostream &os) const override;

private:
    const ContextEmitter _context;
};

// -----------------------------------------------------------------------------

class LogManager {
public:
    static LogManager *getLogManager() { return &global_log_manager; }
    Logger *getLogger(const std::string &name);

private:
    static LogManager global_log_manager;

    // The mutex protects _known_loggers.
    std::mutex _mutex;
    std::unordered_map<std::string, std::unique_ptr<Logger>> _known_loggers;

    Logger *lookup(const std::string &name, Logger *parent);
};

// -----------------------------------------------------------------------------

class LogStream {
public:
    LogStream(Logger *logger, LogLevel level) : _logger(logger), _level(level) {
        // The test and all the similar ones below are just optimizations.
        if (_logger->isLoggable(_level)) {
            _logger->emitContext(_os);
        }
    }

    virtual ~LogStream() {
        if (_logger->isLoggable(_level)) {
            _logger->log(LogRecord(_level, _os.str()));
        }
    }

    template <typename T>
    std::ostream &operator<<(const T &t) {
        return _logger->isLoggable(_level) ? (_os << t) : _os;
    }

protected:
    Logger *const _logger;
    const LogLevel _level;
    std::ostringstream _os;
};

// -----------------------------------------------------------------------------

struct Emergency : public LogStream {
    explicit Emergency(Logger *logger)
        : LogStream(logger, LogLevel::emergency) {}
};

struct Alert : public LogStream {
    explicit Alert(Logger *logger) : LogStream(logger, LogLevel::alert) {}
};

struct Critical : public LogStream {
    explicit Critical(Logger *logger) : LogStream(logger, LogLevel::critical) {}
};

struct Error : public LogStream {
    explicit Error(Logger *logger) : LogStream(logger, LogLevel::error) {}
};

struct Warning : public LogStream {
    explicit Warning(Logger *logger) : LogStream(logger, LogLevel::warning) {}
};

struct Notice : public LogStream {
    explicit Notice(Logger *logger) : LogStream(logger, LogLevel::notice) {}
};

struct Informational : public LogStream {
    explicit Informational(Logger *logger)
        : LogStream(logger, LogLevel::informational) {}
};

struct Debug : public LogStream {
    explicit Debug(Logger *logger) : LogStream(logger, LogLevel::debug) {}
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
