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

#include "ContactgroupsColumn.h"
#include "nagios.h"
#include "Query.h"

void ContactgroupsColumn::output(void *data, Query *query)
{
    query->outputBeginList();

    if (data) {
        data = shiftPointer(data);
        if (data) {
            contactgroupsmember *cgm = *(contactgroupsmember **)((char *)data + _offset);
            bool first = true;
            while (cgm) {
                contactgroup *cg = (contactgroup *)cgm->group_ptr;
                if (!first)
                    query->outputListSeparator();
                else
                    first = false;
                query->outputString(cg->group_name);
                cgm = cgm->next;
            }
        }
    }

    query->outputEndList();
}

void *ContactgroupsColumn::getNagiosObject(char *name)
{
    return find_contactgroup(name);
}

bool ContactgroupsColumn::isNagiosMember(void *data, void *nagobject)
{
    if (!nagobject || !data)
        return false;

    // data is already shifted (_indirect_offset is taken into account)
    // But _offset needs still to be accounted for
    contactgroupsmember *cgm = *(contactgroupsmember **)((char *)data + _offset);

    while (cgm) {
        if (cgm->group_ptr == nagobject)
            return true;
        cgm = cgm->next;
    }
    return false;
}

bool ContactgroupsColumn::isEmpty(void *data)
{
    contactgroupsmember *cgm = *(contactgroupsmember **)((char *)data + _offset);
    return cgm == 0;
}
