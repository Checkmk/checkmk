// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

#ifndef Store_h
#define Store_h

#include "config.h"

#include "TableServices.h"
#include "TableHosts.h"
#include "TableHostgroups.h"
#include "TableServicegroups.h"
#include "TableContacts.h"
#include "TableCommands.h"
#include "TableTimeperiods.h"
#include "TableContactgroups.h"
#include "TableDownComm.h"
#include "TableStatus.h"
#include "TableLog.h"
#include "TableStateHistory.h"
#include "TableColumns.h"
#include "OutputBuffer.h"
#include "InputBuffer.h"
#include "LogCache.h"

class Store
{
    LogCache           _log_cache;
    TableContacts      _table_contacts;
    TableCommands      _table_commands;
    TableHostgroups    _table_hostgroups;
    TableHosts         _table_hosts;
    TableHosts         _table_hostsbygroup;
    TableServicegroups _table_servicegroups;
    TableServices      _table_services;
    TableServices      _table_servicesbygroup;
    TableServices      _table_servicesbyhostgroup;
    TableTimeperiods   _table_timeperiods;
    TableContactgroups _table_contactgroups;
    TableDownComm      _table_downtimes;
    TableDownComm      _table_comments;
    TableStatus        _table_status;
    TableLog           _table_log;
    TableStateHistory  _table_statehistory;
    TableColumns       _table_columns;

    typedef map<string, Table *> _tables_t;
    _tables_t _tables;

public:
    Store();
    LogCache* logCache() { return &_log_cache; };
    void registerHostgroup(hostgroup *);
    void registerComment(nebstruct_comment_data *);
    void registerDowntime(nebstruct_downtime_data *);
    bool answerRequest(InputBuffer *, OutputBuffer *);

private:
    Table *findTable(string name);
    void answerGetRequest(InputBuffer *, OutputBuffer *, const char *);
    void answerCommandRequest(const char *);
};


#endif // Store_h


