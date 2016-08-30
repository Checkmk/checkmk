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
#ifdef CMC
#include <cstdio>
#endif
#include <sstream>
#include <string>

class LogRecord;

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

void open_logfile(const std::string &path);
void close_logfile();
void logger(const LogRecord &record);

#ifdef CMC
void set_log_config(LogLevel level, bool log_microtime);
void reopen_logfile(const std::string &path);
bool isLoggable(LogLevel level);
FILE *get_logfile();
#endif

class LogRecord {
public:
    explicit LogRecord(LogLevel level) : _level(level) {}
    virtual ~LogRecord() { logger(*this); }

    LogLevel getLevel() const { return _level; }
    std::string getMessage() const { return _os.str(); }

#ifdef CMC
    bool isLoggable() const { return ::isLoggable(getLevel()); }
#endif

    template <typename T>
    std::ostream &operator<<(const T &t) {
        return _os << t;
    }

private:
    LogLevel _level;
    std::ostringstream _os;
};

struct Emergency : public LogRecord {
    Emergency() : LogRecord(LogLevel::emergency) {}
};

struct Alert : public LogRecord {
    Alert() : LogRecord(LogLevel::alert) {}
};

struct Critical : public LogRecord {
    Critical() : LogRecord(LogLevel::critical) {}
};

struct Error : public LogRecord {
    Error() : LogRecord(LogLevel::error) {}
};

struct Warning : public LogRecord {
    Warning() : LogRecord(LogLevel::warning) {}
};

struct Notice : public LogRecord {
    Notice() : LogRecord(LogLevel::notice) {}
};

struct Informational : public LogRecord {
    Informational() : LogRecord(LogLevel::informational) {}
};

struct Debug : public LogRecord {
    Debug() : LogRecord(LogLevel::debug) {}
};

#endif  // Logger_h
