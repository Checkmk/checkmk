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

#include "ContactsColumn.h"
#include "nagios.h"
#include "TableContacts.h"
#include "logger.h"
#include "Query.h"
#include "tables.h"

extern contact *contact_list;

void *ContactsColumn::getNagiosObject(char *name)
{
    return (void *)find_contact(name);
}

void ContactsColumn::output(void *data, Query *query)
{
    query->outputBeginList();
    data = shiftPointer(data);

    if (data) {
        bool first = true;

        contact *ctc = contact_list;
        while (ctc) {
            if (isNagiosMember(data, ctc)) {
                if (first)
                    first = false;
                else
                    query->outputListSeparator();
                query->outputString(ctc->name);
            }
            ctc = ctc->next;
        }
    }
    query->outputEndList();
}


bool ContactsColumn::isEmpty(void *svc)
{
    contact *ct = contact_list;
    while (ct) {
        if (isNagiosMember(svc, ct))
            return false;
        ct = ct->next;
    }
    return true;
}

