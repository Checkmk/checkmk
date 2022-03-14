// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Logger_h
#define Logger_h

#include "config.h"  // IWYU pragma: keep

// The stream-related pragmas are probably caused by
// https://github.com/include-what-you-use/include-what-you-use/issues/277
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

    [[nodiscard]] LogLevel getLevel() const { return _level; }
    void setLevel(LogLevel level) { _level = level; }

    [[nodiscard]] std::string getMessage() const { return _message; }
    void setMessage(const std::string &message) { _message = message; }

    [[nodiscard]] std::chrono::system_clock::time_point getTimePoint() const {
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
public:
    void format(std::ostream &os, const LogRecord &record) override;
};

// -----------------------------------------------------------------------------

class Handler {
public:
    virtual ~Handler() { setFormatter(std::unique_ptr<Formatter>()); }
    virtual void publish(const LogRecord &record) = 0;

    [[nodiscard]] std::shared_ptr<Formatter> getFormatter() const {
        return std::atomic_load(&_formatter);
    }
    void setFormatter(std::unique_ptr<Formatter> formatter) {
        std::atomic_store(&_formatter, std::shared_ptr(std::move(formatter)));
    }

private:
    std::shared_ptr<Formatter> _formatter{std::make_shared<SimpleFormatter>()};
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

    [[nodiscard]] bool isLoggable(LogLevel level) const;

    [[nodiscard]] virtual std::string getName() const = 0;

    [[nodiscard]] virtual Logger *getParent() const = 0;

    [[nodiscard]] virtual LogLevel getLevel() const = 0;
    virtual void setLevel(LogLevel level) = 0;

    [[nodiscard]] virtual Handler *getHandler() const = 0;
    virtual void setHandler(std::unique_ptr<Handler> handler) = 0;

    [[nodiscard]] virtual bool getUseParentHandlers() const = 0;
    virtual void setUseParentHandlers(bool useParentHandlers) = 0;

    virtual void emitContext(std::ostream &os) const = 0;

    virtual void log(const LogRecord &record) = 0;
    virtual void callHandler(const LogRecord &record) = 0;
};

class ConcreteLogger : public Logger {
public:
    ConcreteLogger(const std::string &name, Logger *parent);
    ~ConcreteLogger() override;

    [[nodiscard]] std::string getName() const override;

    [[nodiscard]] Logger *getParent() const override;

    [[nodiscard]] LogLevel getLevel() const override;
    void setLevel(LogLevel level) override;

    [[nodiscard]] Handler *getHandler() const override;
    void setHandler(std::unique_ptr<Handler> handler) override;

    [[nodiscard]] bool getUseParentHandlers() const override;
    void setUseParentHandlers(bool useParentHandlers) override;

    void emitContext(std::ostream &os) const override;

    void log(const LogRecord &record) override;

private:
    void callHandler(const LogRecord &record) override;
    const std::string _name;
    Logger *const _parent;
    std::atomic<LogLevel> _level;
    std::atomic<Handler *> _handler;
    std::atomic<bool> _use_parent_handlers;
    std::mutex _lock;
};

class LoggerDecorator : public Logger {
public:
    explicit LoggerDecorator(Logger *logger);

    [[nodiscard]] std::string getName() const override;

    [[nodiscard]] Logger *getParent() const override;

    [[nodiscard]] LogLevel getLevel() const override;
    void setLevel(LogLevel level) override;

    [[nodiscard]] Handler *getHandler() const override;
    void setHandler(std::unique_ptr<Handler> handler) override;

    [[nodiscard]] bool getUseParentHandlers() const override;
    void setUseParentHandlers(bool useParentHandlers) override;

    void emitContext(std::ostream &os) const override;

    void log(const LogRecord &record) override;

protected:
    Logger *const _logger;

private:
    void callHandler(const LogRecord &record) override;
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

class ThreadNameLogger : public ContextLogger {
public:
    explicit ThreadNameLogger(Logger *logger);
    explicit ThreadNameLogger(const std::string &name);
};

// -----------------------------------------------------------------------------

class LogManager {
public:
    static LogManager *getLogManager() { return &global_log_manager; }
    Logger *getLogger(const std::string &name);

private:
    // NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
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

    // NOTE: Tricky stuff ahead... It is crucial that we return a LogStream&
    // here and not a std::ostream&, as one might naively expect. Think about:
    //
    //     Bar bar;
    //     Debug(logger) << "foo" << bar;
    //
    // Bar can have an expensive operator<<, so we must avoid calling it when we
    // don't have to. We don't want to guard any logging statement like:
    //
    //     Bar bar;
    //     if (logger.isLoggable(LogLevel::debug)) {
    //         Debug(logger) << "foo" << bar;
    //     }
    //
    // We could even go a step further and return a no-op stream after we have
    // detected that we don't have to log (under the assumption that the log
    // level stays unchagend during logging, which it better should). But this
    // doesn't really seem necessary, Logger::isLoggable is very cheap.
    template <typename T>
    LogStream &operator<<(const T &t) {
        if (_logger->isLoggable(_level)) {
            _os << t;
        }
        return *this;
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

    generic_error(int err, const char *what_arg)
        : std::system_error(err, std::generic_category(), what_arg) {}

    explicit generic_error(const char *what_arg)
        : generic_error(errno, what_arg) {}

    generic_error(int err, const std::string &what_arg)
        : std::system_error(err, std::generic_category(), what_arg) {}

    explicit generic_error(const std::string &what_arg)
        : generic_error(errno, what_arg) {}
};
std::ostream &operator<<(std::ostream &os, const generic_error &ge);

#endif  // Logger_h
