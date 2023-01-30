// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableLabels.h"

#include <memory>

#include "livestatus/Column.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"

namespace {
struct NameValue {
    const std::string &name;
    const std::string &value;
};
}  // namespace

TableLabels::TableLabels(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{});
}

std::string TableLabels::name() const { return "labels"; }

std::string TableLabels::namePrefix() const { return "label_"; }

// static
void TableLabels::addColumns(Table *table, const std::string &prefix,
                             const ColumnOffsets &offsets) {
    table->addColumn(std::make_unique<StringColumn<NameValue>>(
        prefix + "name", "The name of the label", offsets,
        [](const NameValue &r) { return r.name; }));
    table->addColumn(std::make_unique<StringColumn<NameValue>>(
        prefix + "value", "The value of the label", offsets,
        [](const NameValue &r) { return r.value; }));
}

void TableLabels::answerQuery(Query &query, const User & /*user*/) {
    core()->forEachLabelUntil(
        [&query](const std::string &name, const std::string &value) {
            // TODO(sp): Use user.is_authorized_for_object!
            NameValue r{name, value};
            return query.processDataset(Row{&r});
        });
}
