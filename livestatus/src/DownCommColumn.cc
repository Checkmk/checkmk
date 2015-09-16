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

#include "DownCommColumn.h"
#include "DowntimeOrComment.h"
#include "TableDownComm.h"
#include "logger.h"
#include "Query.h"
#include "tables.h"

void DownCommColumn::output(void *data, Query *query)
{
    TableDownComm *table = _is_downtime ? g_table_downtimes : g_table_comments;
    query->outputBeginList();
    data = shiftPointer(data); // points to host or service
    if (data)
    {
        bool first = true;
        bool found_match = false;

        for (map<pair<unsigned long, bool>, DowntimeOrComment *>::iterator it = table->entriesIteratorBegin();
                it != table->entriesIteratorEnd();
                ++it)
        {
            unsigned long id     = it->first.first;
            bool is_service       =  it->first.second;
            DowntimeOrComment *dt =  it->second;

            found_match = false;

            if (!is_service){
                if (dt->_host->name == ((host*)data)->name)
                    found_match = true;
            }
            else
               if ( dt->_service->description == ((service*)data)->description && dt->_service->host_name == ((service*)data)->host_name )
                    found_match = true;

            if (found_match)
            {
                if (first)
                    first = false;
                else
                    query->outputListSeparator();
                if (_with_info)
                {
                    query->outputBeginSublist();
                    query->outputUnsignedLong(id);
                    query->outputSublistSeparator();
                    query->outputString(dt->_author_name);
                    query->outputSublistSeparator();
                    query->outputString(dt->_comment);
                    if(_with_extra_info && !_is_downtime) {
                        query->outputSublistSeparator();
                        query->outputInteger(((Comment*)dt)->_entry_type);
                        query->outputSublistSeparator();
                        query->outputTime(dt->_entry_time);
                    }
                    query->outputEndSublist();
                }
                else
                    query->outputUnsignedLong(id);
            }
        }
    }
    query->outputEndList();
}

void *DownCommColumn::getNagiosObject(char *name)
{
    unsigned int id = strtoul(name, 0, 10);
    return (void *)id; // Hack. Convert number into pointer.
}

bool DownCommColumn::isNagiosMember(void *data, void *member)
{
    TableDownComm *table = _is_downtime ? g_table_downtimes : g_table_comments;
    // data points to a host or service
    // member is not a pointer, but an unsigned int (hack)
    int64_t id = (int64_t)member; // Hack. Convert it back.
    DowntimeOrComment *dt = table->findEntry(id, _is_service);
    return dt != 0 &&
        ( dt->_service == (service *)data || (dt->_service == 0 && dt->_host == (host *)data));
}

bool DownCommColumn::isEmpty(void *data)
{
    if (!data) return true;

    TableDownComm *table = _is_downtime ? g_table_downtimes : g_table_comments;
    for (map<pair<unsigned long, bool>, DowntimeOrComment *>::iterator it = table->entriesIteratorBegin();
            it != table->entriesIteratorEnd();
            ++it)
    {
        DowntimeOrComment *dt = it->second;
        if ((void *)dt->_service == data ||
                (dt->_service == 0 && dt->_host == data))
        {
            return false;
        }
    }
    return true; // empty
}
