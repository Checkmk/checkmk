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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Logger_h
#define Logger_h

#include "config.h"  // IWYU pragma: keep
#include <sstream>
#include "logger.h"

class Logger {
public:
    explicit Logger(int priority) : _priority(priority) {}
    ~Logger() { logger(_priority, "%s", _os.str().c_str()); }

    template <typename T>
    std::ostream &operator<<(const T &t) {
        return _os << t;
    }

private:
    int _priority;
    std::ostringstream _os;
};

struct Emergency : public Logger {
    Emergency() : Logger(LOG_EMERG) {}
};

struct Alert : public Logger {
    Alert() : Logger(LOG_ALERT) {}
};

struct Critical : public Logger {
    Critical() : Logger(LOG_CRIT) {}
};

struct Error : public Logger {
    Error() : Logger(LOG_ERR) {}
};

struct Warning : public Logger {
    Warning() : Logger(LOG_WARNING) {}
};

struct Notice : public Logger {
    Notice() : Logger(LOG_NOTICE) {}
};

struct Informational : public Logger {
    Informational() : Logger(LOG_INFO) {}
};

struct Debug : public Logger {
    Debug() : Logger(LOG_DEBUG) {}
};

#endif  // Logger_h
