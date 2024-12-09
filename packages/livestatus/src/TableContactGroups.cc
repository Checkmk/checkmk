// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableContactGroups.h"

#include <functional>
#include <memory>
#include <vector>

#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/ListColumn.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"

using row_type = IContactGroup;

TableContactGroups::TableContactGroups() {
    const ColumnOffsets offsets{};
    addColumn(std::make_unique<StringColumn<row_type>>(
        "name", "Name of the contact group", offsets,
        [](const row_type &row) { return row.name(); }));
    addColumn(std::make_unique<StringColumn<row_type>>(
        "alias", "An alias of the contact group", offsets,
        [](const row_type &row) { return row.alias(); }));
    addColumn(std::make_unique<ListColumn<row_type>>(
        "members", "A list of all members of this contactgroup", offsets,
        [](const row_type &row) { return row.contactNames(); }));
}

std::string TableContactGroups::name() const { return "contactgroups"; }

std::string TableContactGroups::namePrefix() const { return "contactgroup_"; }

void TableContactGroups::answerQuery(Query &query, const User & /*user*/,
                                     const ICore &core) {
    core.all_of_contact_groups([&query](const row_type &row) {
        return query.processDataset(Row{&row});
    });
}

Row TableContactGroups::get(const std::string &primary_key,
                            const ICore &core) const {
    // "name" is the primary key
    return Row{core.find_contactgroup(primary_key)};
}
