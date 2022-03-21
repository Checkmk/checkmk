// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableHostsByGroup.h"

#include "Column.h"
#include "MonitoringCore.h"
#include "NagiosGlobals.h"
#include "Query.h"
#include "Row.h"
#include "TableHostGroups.h"
#include "TableHosts.h"
#include "auth.h"
#include "nagios.h"

namespace {
struct hostbygroup {
    const host *hst;
    const hostgroup *host_group;
};
}  // namespace

TableHostsByGroup::TableHostsByGroup(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    TableHosts::addColumns(this, "", offsets.add([](Row r) {
        return r.rawData<hostbygroup>()->hst;
    }));
    TableHostGroups::addColumns(this, "hostgroup_", offsets.add([](Row r) {
        return r.rawData<hostbygroup>()->host_group;
    }));
}

std::string TableHostsByGroup::name() const { return "hostsbygroup"; }

std::string TableHostsByGroup::namePrefix() const { return "host_"; }

void TableHostsByGroup::answerQuery(Query *query) {
    for (const hostgroup *hg = hostgroup_list; hg != nullptr; hg = hg->next) {
        if (is_authorized_for_host_group(core()->groupAuthorization(),
                                         core()->serviceAuthorization(), hg,
                                         query->authUser())) {
            for (const hostsmember *m = hg->members; m != nullptr;
                 m = m->next) {
                hostbygroup hbg{m->host_ptr, hg};
                if (!query->processDataset(Row(&hbg))) {
                    return;
                }
            }
        }
    }
}

bool TableHostsByGroup::isAuthorized(Row row, const contact *ctc) const {
    return is_authorized_for(core()->serviceAuthorization(), ctc,
                             rowData<hostbygroup>(row)->hst, nullptr);
}
