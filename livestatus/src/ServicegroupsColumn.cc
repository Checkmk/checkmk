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

#include "ServicegroupsColumn.h"
#include "nagios.h"
#include "Query.h"

objectlist *ServicegroupsColumn::getData(void *data)
{
    if (data) {
        data = shiftPointer(data);
        if (data)
            return *(objectlist **)((char *)data + _offset);
    }
    return 0;
}

void ServicegroupsColumn::output(void *data, Query *query)
{
    query->outputBeginList();
    objectlist *list = getData(data);
    if (list) {
        bool first = true;
        while (list) {
            servicegroup *sg = (servicegroup *)list->object_ptr;
            if (!first)
                query->outputListSeparator();
            else
                first = false;
            query->outputString(sg->group_name);
            list = list->next;
        }
    }
    query->outputEndList();
}

void *ServicegroupsColumn::getNagiosObject(char *name)
{
    return find_servicegroup(name);
}

bool ServicegroupsColumn::isNagiosMember(void *data, void *nagobject)
{
    // data is already shifted
    objectlist *list = *(objectlist **)((char *)data + _offset);
    while (list) {
        if (list->object_ptr == nagobject)
            return true;
        list = list->next;
    }
    return false;
}

bool ServicegroupsColumn::isEmpty(void *data)
{
    objectlist *list = *(objectlist **)((char *)data + _offset);
    return list == 0;
}
