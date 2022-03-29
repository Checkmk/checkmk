// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableContactGroups.h"

#include <memory>
#include <vector>

#include "Column.h"
#include "ListColumn.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "StringColumn.h"
#include "nagios.h"

TableContactGroups::TableContactGroups(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<contactgroup>>(
        "name", "Name of the contact group", offsets,
        [](const contactgroup &r) {
            return r.group_name == nullptr ? "" : r.group_name;
        }));
    addColumn(std::make_unique<StringColumn<contactgroup>>(
        "alias", "An alias of the contact group", offsets,
        [](const contactgroup &r) {
            return r.alias == nullptr ? "" : r.alias;
        }));
    addColumn(std::make_unique<ListColumn<contactgroup>>(
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

void TableContactGroups::answerQuery(Query &query, const User & /*user*/) {
    for (const auto *cg = contactgroup_list; cg != nullptr; cg = cg->next) {
        const contactgroup *r = cg;
        if (!query.processDataset(Row{r})) {
            break;
        }
    }
}

Row TableContactGroups::get(const std::string &primary_key) const {
    // "name" is the primary key
    return Row(core()->find_contactgroup(primary_key));
}
