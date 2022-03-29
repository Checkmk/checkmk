// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableHostsByGroup.h"

#include "Column.h"
#include "Query.h"
#include "Row.h"
#include "TableHostGroups.h"
#include "TableHosts.h"
#include "auth.h"
#include "nagios.h"

namespace {
struct host_and_group {
    const host *hst;
    const hostgroup *group;
};
}  // namespace

TableHostsByGroup::TableHostsByGroup(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    TableHosts::addColumns(this, "", offsets.add([](Row r) {
        return r.rawData<host_and_group>()->hst;
    }));
    TableHostGroups::addColumns(this, "hostgroup_", offsets.add([](Row r) {
        return r.rawData<host_and_group>()->group;
    }));
}

std::string TableHostsByGroup::name() const { return "hostsbygroup"; }

std::string TableHostsByGroup::namePrefix() const { return "host_"; }

void TableHostsByGroup::answerQuery(Query *query, const User &user) {
    for (const auto *grp = hostgroup_list; grp != nullptr; grp = grp->next) {
        if (user.is_authorized_for_host_group(*grp)) {
            for (const auto *m = grp->members; m != nullptr; m = m->next) {
                const auto *hst = m->host_ptr;
                if (user.is_authorized_for_host(*hst)) {
                    host_and_group hag{hst, grp};
                    if (!query->processDataset(Row{&hag})) {
                        return;
                    }
                }
            }
        }
    }
}
