// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableContactGroups.h"

#include <memory>
#include <variant>  // IWYU pragma: keep
#include <vector>

#include "livestatus/Column.h"
#include "livestatus/Interface.h"
#include "livestatus/ListColumn.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/StringColumn.h"

TableContactGroups::TableContactGroups(MonitoringCore *mc) : Table(mc) {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<IContactGroup>>(
        "name", "Name of the contact group", offsets,
        [](const IContactGroup &r) { return r.name(); }));
    addColumn(std::make_unique<StringColumn<IContactGroup>>(
        "alias", "An alias of the contact group", offsets,
        [](const IContactGroup &r) { return r.alias(); }));
    addColumn(std::make_unique<ListColumn<IContactGroup>>(
        "members", "A list of all members of this contactgroup", offsets,
        [](const IContactGroup &r) { return r.contactNames(); }));
}

std::string TableContactGroups::name() const { return "contactgroups"; }

std::string TableContactGroups::namePrefix() const { return "contactgroup_"; }

void TableContactGroups::answerQuery(Query &query, const User & /*user*/) {
    core()->all_of_contact_groups([&query](const IContactGroup &r) {
        return query.processDataset(Row{&r});
    });
}

Row TableContactGroups::get(const std::string &primary_key) const {
    // "name" is the primary key
    return Row{core()->find_contactgroup(primary_key)};
}
