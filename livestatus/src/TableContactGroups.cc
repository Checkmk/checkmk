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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableContactGroups.h"
#include "ContactGroupsMemberColumn.h"
#include "MonitoringCore.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "nagios.h"

using std::string;

extern contactgroup *contactgroup_list;

TableContactgroups::TableContactgroups(MonitoringCore *core)
    : Table(core->loggerLivestatus()), _core(core) {
    contactgroup cg;
    char *ref = reinterpret_cast<char *>(&cg);
    addColumn(
        new OffsetStringColumn("name", "The name of the contactgroup",
                               reinterpret_cast<char *>(&cg.group_name) - ref));
    addColumn(
        new OffsetStringColumn("alias", "The alias of the contactgroup",
                               reinterpret_cast<char *>(&cg.alias) - ref));
    addColumn(new ContactgroupsMemberColumn(
        "members", "A list of all members of this contactgroup", -1));
}

string TableContactgroups::name() const { return "contactgroups"; }

string TableContactgroups::namePrefix() const { return "contactgroup_"; }

void TableContactgroups::answerQuery(Query *query) {
    for (contactgroup *cg = contactgroup_list; cg != nullptr; cg = cg->next) {
        if (!query->processDataset(cg)) {
            break;
        }
    }
}

void *TableContactgroups::findObject(const string &objectspec) {
    return _core->find_contactgroup(objectspec);
}
