// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Logger_h
#define Logger_h

#include <sys/stat.h>
#include <sys/time.h>

#include "LoggerAdaptor.h"

class WinApiAdaptor;

typedef void *HANDLE;

class Logger : public LoggerAdaptor {
public:
    explicit Logger(const WinApiAdaptor &winapi);
    virtual ~Logger() = default;
    Logger(const Logger &) = delete;
    Logger &operator=(const Logger &) = delete;

private:
    bool _verbose_mode;
    bool _found_crash;

    // Mutex for crash.log
    const HANDLE _crashlogMutex;
    const WinApiAdaptor &_winapi;

    std::string _crash_log;
    std::string _connection_log;
    std::string _success_log;

    // Pointer to open crash log file, if crash_debug = on
    HANDLE _connectionlog_file;
    struct timeval _crashlog_start;

    inline void lockCrashLog() const;
    inline void unlockCrashLog() const;

public:
    // log messages to stdout if verbose mode is active
    virtual void verbose(const char *format, ...) const override
        __attribute__((format(gnu_printf, 2, 3)));

    // log messages to the crash log file if crashLog is active
    virtual void crashLog(const char *format, ...) const override
        __attribute__((format(gnu_printf, 2, 3)));

    virtual void openCrashLog(const std::string &log_directory) override;
    virtual void closeCrashLog() const override;
    virtual void printCrashLog(std::ostream &out) override;

    virtual inline void setVerbose(bool value) override {
        _verbose_mode = value;
    }

    virtual inline bool getVerbose() const override { return _verbose_mode; }

    virtual std::array<std::string, 3> getLogFilenames() const override;
};

#endif  // Logger_h
