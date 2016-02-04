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

#include "ContactgroupsColumn.h"
#include "Query.h"
#include "nagios.h"

void ContactgroupsColumn::output(void *data, Query *query) {
    query->outputBeginList();

    if (data != nullptr) {
        data = shiftPointer(data);
        if (data != nullptr) {
            contactgroupsmember *cgm =
                *reinterpret_cast<contactgroupsmember **>(
                    reinterpret_cast<char *>(data) + _offset);
            bool first = true;
            while (cgm != nullptr) {
                contactgroup *cg = cgm->group_ptr;
                if (!first) {
                    query->outputListSeparator();
                } else {
                    first = false;
                }
                query->outputString(cg->group_name);
                cgm = cgm->next;
            }
        }
    }

    query->outputEndList();
}

void *ContactgroupsColumn::getNagiosObject(char *name) {
    return find_contactgroup(name);
}

bool ContactgroupsColumn::isNagiosMember(void *data, void *nagobject) {
    if ((nagobject == nullptr) || (data == nullptr)) {
        return false;
    }

    // data is already shifted (_indirect_offset is taken into account)
    // But _offset needs still to be accounted for
    contactgroupsmember *cgm = *reinterpret_cast<contactgroupsmember **>(
        reinterpret_cast<char *>(data) + _offset);

    while (cgm != nullptr) {
        if (cgm->group_ptr == nagobject) {
            return true;
        }
        cgm = cgm->next;
    }
    return false;
}

bool ContactgroupsColumn::isEmpty(void *data) {
    contactgroupsmember *cgm = *reinterpret_cast<contactgroupsmember **>(
        reinterpret_cast<char *>(data) + _offset);
    return cgm == nullptr;
}
