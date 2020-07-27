// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableContactGroups.h"

#include <memory>
#include <vector>

#include "Column.h"
#include "ListLambdaColumn.h"
#include "MonitoringCore.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "nagios.h"

extern contactgroup *contactgroup_list;

TableContactGroups::TableContactGroups(MonitoringCore *mc) : Table(mc) {
    Column::Offsets offsets{};
    addColumn(std::make_unique<OffsetStringColumn>(
        "name", "The name of the contactgroup",
        Column::Offsets{-1, -1, -1,
                        DANGEROUS_OFFSETOF(contactgroup, group_name)}));
    addColumn(std::make_unique<OffsetStringColumn>(
        "alias", "The alias of the contactgroup",
        Column::Offsets{-1, -1, -1, DANGEROUS_OFFSETOF(contactgroup, alias)}));
    addColumn(std::make_unique<ListLambdaColumn<contactgroup>>(
        "members", "A list of all members of this contactgroup", offsets,
        [](const contactgroup &r) {
            std::vector<std::string> names;
            for (const auto *cm = r.members; cm != nullptr; cm = cm->next) {
                names.emplace_back(cm->contact_ptr->name);
            }
            return names;
        }));
}

std::string TableContactGroups::name() const { return "contactgroups"; }

std::string TableContactGroups::namePrefix() const { return "contactgroup_"; }

void TableContactGroups::answerQuery(Query *query) {
    for (const auto *cg = contactgroup_list; cg != nullptr; cg = cg->next) {
        const contactgroup *r = cg;
        if (!query->processDataset(Row(r))) {
            break;
        }
    }
}

Row TableContactGroups::findObject(const std::string &objectspec) const {
    // TODO(sp): Remove ugly cast.
    return Row(reinterpret_cast<contactgroup *>(
        core()->find_contactgroup(objectspec)));
}
