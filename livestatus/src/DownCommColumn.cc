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
                if (dt->_host->name == ((host_struct*)data)->name)
                    found_match = true;
            }
            else
               if ( dt->_service->description == ((service_struct*)data)->description && dt->_service->host_name == ((service_struct*)data)->host_name )
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
