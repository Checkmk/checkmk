// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableServicesByHostGroup.h"
#include "Query.h"
#include "Row.h"
#include "TableHostGroups.h"
#include "TableServices.h"
#include "auth.h"
#include "nagios.h"

extern hostgroup *hostgroup_list;

namespace {
struct servicebyhostgroup {
    service svc;
    // cppcheck is too dumb to see usage in the DANGEROUS_OFFSETOF macro
    // cppcheck-suppress unusedStructMember
    hostgroup *host_group;
};
}  // namespace

TableServicesByHostGroup::TableServicesByHostGroup(MonitoringCore *mc)
    : Table(mc) {
    TableServices::addColumns(this, "", -1, true);
    TableHostGroups::addColumns(
        this, "hostgroup_", DANGEROUS_OFFSETOF(servicebyhostgroup, host_group));
}

std::string TableServicesByHostGroup::name() const {
    return "servicesbyhostgroup";
}

std::string TableServicesByHostGroup::namePrefix() const { return "service_"; }

void TableServicesByHostGroup::answerQuery(Query *query) {
    for (hostgroup *hg = hostgroup_list; hg != nullptr; hg = hg->next) {
        for (hostsmember *mem = hg->members; mem != nullptr; mem = mem->next) {
            for (servicesmember *smem = mem->host_ptr->services;
                 smem != nullptr; smem = smem->next) {
                servicebyhostgroup sbhg = {*smem->service_ptr, hg};
                if (!query->processDataset(Row(&sbhg))) {
                    return;
                }
            }
        }
    }
}

bool TableServicesByHostGroup::isAuthorized(Row row, const contact *ctc) const {
    auto svc = &rowData<servicebyhostgroup>(row)->svc;
    return is_authorized_for(core(), ctc, svc->host_ptr, svc);
}
