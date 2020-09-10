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
#include "Query.h"
#include "StringLambdaColumn.h"
#include "nagios.h"

TableContactGroups::TableContactGroups(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<StringLambdaColumn<contactgroup>>(
        "name", "The name of the contactgroup", offsets,
        [](const contactgroup &r) {
            return r.group_name == nullptr ? "" : r.group_name;
        }));
    addColumn(std::make_unique<StringLambdaColumn<contactgroup>>(
        "alias", "The alias of the contactgroup", offsets,
        [](const contactgroup &r) {
            return r.alias == nullptr ? "" : r.alias;
        }));
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
    extern contactgroup *contactgroup_list;
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
