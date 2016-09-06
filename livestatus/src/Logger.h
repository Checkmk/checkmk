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
#include <cerrno>
#include <chrono>
#include <fstream>  // IWYU pragma: keep
#include <memory>
#include <mutex>
#include <sstream>  // IWYU pragma: keep
#include <string>
#include <system_error>

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

class Formatter {
public:
    virtual ~Formatter() = default;
    virtual std::string format(const LogRecord &record) const = 0;
};

class SimpleFormatter : public Formatter {
    friend class Handler;
    std::string format(const LogRecord &record) const override;
};

class Handler {
public:
    virtual ~Handler() = default;
    virtual void publish(const LogRecord &record) = 0;

    Formatter *getFormatter();
    void setFormatter(std::unique_ptr<Formatter> formatter);

protected:
    Handler();

private:
    std::mutex _mutex;
    std::unique_ptr<Formatter> _formatter;
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

class Logger {
public:
    static Logger *getLogger() { return &_global_logger; }

    LogLevel getLevel();
#ifdef CMC
    void setLevel(LogLevel level);

    Handler *getHandler();
#endif
    void setHandler(std::unique_ptr<Handler> handler);

#ifdef CMC
    bool isLoggable(LogLevel level);
#endif
    void log(const LogRecord &record);

private:
    static Logger _global_logger;

    std::mutex _mutex;
    LogLevel _level;
    std::unique_ptr<Handler> _handler;

    Logger();
};

// -----------------------------------------------------------------------------

class LogStream {
public:
    explicit LogStream(LogLevel level) : _level(level) {}
    virtual ~LogStream() {
        Logger::getLogger()->log(LogRecord(_level, _os.str()));
    }

    template <typename T>
    std::ostream &operator<<(const T &t) {
        return _os << t;
    }

private:
    LogLevel _level;
    std::ostringstream _os;
};

struct Emergency : public LogStream {
    Emergency() : LogStream(LogLevel::emergency) {}
};

struct Alert : public LogStream {
    Alert() : LogStream(LogLevel::alert) {}
};

struct Critical : public LogStream {
    Critical() : LogStream(LogLevel::critical) {}
};

struct Error : public LogStream {
    Error() : LogStream(LogLevel::error) {}
};

struct Warning : public LogStream {
    Warning() : LogStream(LogLevel::warning) {}
};

struct Notice : public LogStream {
    Notice() : LogStream(LogLevel::notice) {}
};

struct Informational : public LogStream {
    Informational() : LogStream(LogLevel::informational) {}
};

struct Debug : public LogStream {
    Debug() : LogStream(LogLevel::debug) {}
};

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
