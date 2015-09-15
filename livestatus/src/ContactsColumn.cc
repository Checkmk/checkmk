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

