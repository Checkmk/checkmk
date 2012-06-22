// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

#ifndef TableLog_h
#define TableLog_h

#include <map>
#include <time.h>
#include "config.h"
#include "Table.h"

class Logfile;

class TableLog : public Table
{
    typedef map<time_t, Logfile *> _logfiles_t;
    _logfiles_t _logfiles;

public:
    TableLog();
    ~TableLog(){};
    const char *name() { return "log"; }
    const char *prefixname() { return "logs"; }
    bool isAuthorized(contact *ctc, void *data);
    void answerQuery(Query *query);
    Column *column(const char *colname); // override in order to handle current_

private:
    bool answerQuery(Query *, Logfile *, time_t, time_t);
};

#endif // TableLog_h
