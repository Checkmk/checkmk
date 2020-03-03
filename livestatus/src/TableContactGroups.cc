// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableContactGroups.h"
#include <memory>
#include "Column.h"
#include "ContactGroupsMemberColumn.h"
#include "MonitoringCore.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "nagios.h"

extern contactgroup *contactgroup_list;

TableContactGroups::TableContactGroups(MonitoringCore *mc) : Table(mc) {
    addColumn(std::make_unique<OffsetStringColumn>(
        "name", "The name of the contactgroup",
        Column::Offsets{-1, -1, -1,
                        DANGEROUS_OFFSETOF(contactgroup, group_name)}));
    addColumn(std::make_unique<OffsetStringColumn>(
        "alias", "The alias of the contactgroup",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(contactgroup, alias)}));
    addColumn(std::make_unique<ContactGroupsMemberColumn>(
        "members", "A list of all members of this contactgroup",
        Column::Offsets{}));
}

std::string TableContactGroups::name() const { return "contactgroups"; }

std::string TableContactGroups::namePrefix() const { return "contactgroup_"; }

void TableContactGroups::answerQuery(Query *query) {
    for (contactgroup *cg = contactgroup_list; cg != nullptr; cg = cg->next) {
        if (!query->processDataset(Row(cg))) {
            break;
        }
    }
}

Row TableContactGroups::findObject(const std::string &objectspec) const {
    // TODO(sp): Remove ugly cast.
    return Row(reinterpret_cast<contactgroup *>(
        core()->find_contactgroup(objectspec)));
}
