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


#ifndef LoggerAdaptor_h
#define LoggerAdaptor_h

#include <array>
#include <iostream>
#include <string>

class LoggerAdaptor {
public:
    LoggerAdaptor() = default;
    virtual ~LoggerAdaptor() = default;
    LoggerAdaptor(const LoggerAdaptor&) = delete;
    LoggerAdaptor& operator=(const LoggerAdaptor&) = delete;

    // log messages to stdout if verbose mode is active
    virtual void verbose(const char *format, ...) const = 0;
    
    // log messages to the crash log file if crashLog is active
    virtual void crashLog(const char *format, ...) const = 0;
    
    virtual void openCrashLog(const std::string &log_directory) = 0;
    virtual void closeCrashLog() const = 0;
    virtual void printCrashLog(std::ostream &out) = 0;

    virtual void setVerbose(bool value) = 0;
    virtual bool getVerbose() const = 0;
    virtual std::array<std::string, 3> getLogFilenames() const = 0;
};

#endif // LoggerAdaptor_h
