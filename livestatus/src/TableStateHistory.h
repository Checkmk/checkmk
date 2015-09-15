// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include <map>
#include <time.h>
#include "config.h"
#include "string.h"
#include "logger.h"
#include "nagios.h"
#include "Logfile.h"
#include "LogCache.h"
#include "Query.h"

#define CLASSMASK_STATEHIST 0xC6

class HostServiceState;

class TableStateHistory : public Table
{
    int      _query_timeframe;
    Query   *_query;
    int      _since;
    int      _until;

    // Notification periods information, name: active(1)/inactive(0)
    typedef map<string, int> _notification_periods_t;
    _notification_periods_t  _notification_periods;

    // Helper functions to traverse through logfiles
    _logfiles_t::iterator         _it_logs;
    logfile_entries_t            *_entries;
    logfile_entries_t::iterator   _it_entries;
    LogEntry                     *_current_entry;

protected:
    bool     _abort_query;

public:
    TableStateHistory();
    const char *name() { return "statehist"; }
    const char *prefixname() { return "statehist_"; }
    bool isAuthorized(contact *ctc, void *data);
    void handleNewMessage(Logfile *logfile, time_t since, time_t until, unsigned logclasses);
    void answerQuery(Query *query);
    Column *column(const char *colname); // override in order to handle current_
    int updateHostServiceState(Query *query, const LogEntry *entry, HostServiceState *state, const bool only_update);
    static void addColumns(Table *);

private:
    LogEntry* getPreviousLogentry();
    LogEntry* getNextLogentry();
    void      process(Query *query, HostServiceState *hs_state);
    bool      objectFilteredOut(Query *, void *entry);
};


#endif // TableStateHistory_h
