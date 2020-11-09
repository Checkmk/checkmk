// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableHostGroups.h"

#include <memory>

#include "Column.h"
#include "HostListColumn.h"
#include "HostListStateColumn.h"
#include "Query.h"
#include "StringLambdaColumn.h"
#include "auth.h"
#include "nagios.h"

/* this might be a hack (accessing Nagios' internal structures.
   Hi Ethan: please help me here: how should this be code to be
   portable? */
extern hostgroup *hostgroup_list;

TableHostGroups::TableHostGroups(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{});
}

std::string TableHostGroups::name() const { return "hostgroups"; }

std::string TableHostGroups::namePrefix() const { return "hostgroup_"; }

// static
void TableHostGroups::addColumns(Table *table, const std::string &prefix,
                                 const ColumnOffsets &offsets) {
    auto offsets_members{
        offsets.add([](Row r) { return &r.rawData<hostgroup>()->members; })};
    table->addColumn(std::make_unique<StringLambdaColumn<hostgroup>>(
        prefix + "name", "Name of the hostgroup", offsets,
        [](const hostgroup &r) {
            return r.group_name == nullptr ? "" : r.group_name;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<hostgroup>>(
        prefix + "alias", "An alias of the hostgroup", offsets,
        [](const hostgroup &r) { return r.alias == nullptr ? "" : r.alias; }));
    table->addColumn(std::make_unique<StringLambdaColumn<hostgroup>>(
        prefix + "notes", "Optional notes to the hostgroup", offsets,
        [](const hostgroup &r) { return r.notes == nullptr ? "" : r.notes; }));
    table->addColumn(std::make_unique<StringLambdaColumn<hostgroup>>(
        prefix + "notes_url",
        "An optional URL with further information about the hostgroup", offsets,
        [](const hostgroup &r) {
            return r.notes_url == nullptr ? "" : r.notes_url;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<hostgroup>>(
        prefix + "action_url",
        "An optional URL to custom actions or information about the hostgroup",
        offsets, [](const hostgroup &r) {
            return r.action_url == nullptr ? "" : r.action_url;
        }));
    table->addColumn(std::make_unique<HostListColumn>(
        prefix + "members",
        "A list of all host names that are members of the hostgroup",
        offsets_members, table->core(), false));
    table->addColumn(std::make_unique<HostListColumn>(
        prefix + "members_with_state",
        "A list of all host names that are members of the hostgroup together with state and has_been_checked",
        offsets_members, table->core(), true));

    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "worst_host_state",
        "The worst state of all of the groups' hosts (UP <= UNREACHABLE <= DOWN)",
        offsets_members, table->core(),
        HostListStateColumn::Type::worst_hst_state));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_hosts", "The total number of hosts in the group",
        offsets_members, table->core(), HostListStateColumn::Type::num_hst));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_hosts_pending",
        "The number of hosts in the group that are pending", offsets_members,
        table->core(), HostListStateColumn::Type::num_hst_pending));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_hosts_up", "The number of hosts in the group that are up",
        offsets_members, table->core(), HostListStateColumn::Type::num_hst_up));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_hosts_down",
        "The number of hosts in the group that are down", offsets_members,
        table->core(), HostListStateColumn::Type::num_hst_down));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_hosts_unreach",
        "The number of hosts in the group that are unreachable",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_hst_unreach));

    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services",
        "The total number of services of hosts in this group", offsets_members,
        table->core(), HostListStateColumn::Type::num_svc));

    // soft states
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "worst_service_state",
        "The worst state of all services that belong to a host of this group (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets_members, table->core(),
        HostListStateColumn::Type::worst_svc_state));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_pending",
        "The total number of services with the state Pending of hosts in this group",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_pending));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_hosts_handled_problems",
        "The total number of hosts in this group with handled problems",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_hst_handled_problems));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_handled_problems",
        "The total number of services of hosts in this group with handled problems",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_handled_problems));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_hosts_unhandled_problems",
        "The total number of hosts in this group with unhandled problems",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_hst_unhandled_problems));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_unhandled_problems",
        "The total number of services of hosts in this group with unhandled problems",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_unhandled_problems));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_ok",
        "The total number of services with the state OK of hosts in this group",
        offsets_members, table->core(), HostListStateColumn::Type::num_svc_ok));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_warn",
        "The total number of services with the state WARN of hosts in this group",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_warn));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_crit",
        "The total number of services with the state CRIT of hosts in this group",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_crit));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_unknown",
        "The total number of services with the state UNKNOWN of hosts in this group",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_unknown));

    // hard state
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "worst_service_hard_state",
        "The worst state of all services that belong to a host of this group (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets_members, table->core(),
        HostListStateColumn::Type::worst_svc_hard_state));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_hard_ok",
        "The total number of services with the state OK of hosts in this group",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_hard_ok));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_hard_warn",
        "The total number of services with the state WARN of hosts in this group",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_hard_warn));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_hard_crit",
        "The total number of services with the state CRIT of hosts in this group",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_hard_crit));
    table->addColumn(std::make_unique<HostListStateColumn>(
        prefix + "num_services_hard_unknown",
        "The total number of services with the state UNKNOWN of hosts in this group",
        offsets_members, table->core(),
        HostListStateColumn::Type::num_svc_hard_unknown));
}

void TableHostGroups::answerQuery(Query *query) {
    for (const auto *hg = hostgroup_list; hg != nullptr; hg = hg->next) {
        const hostgroup *r = hg;
        if (!query->processDataset(Row(r))) {
            break;
        }
    }
}

Row TableHostGroups::findObject(const std::string &objectspec) const {
    return Row(find_hostgroup(const_cast<char *>(objectspec.c_str())));
}

bool TableHostGroups::isAuthorized(Row row, const contact *ctc) const {
    return is_authorized_for_host_group(core(), rowData<hostgroup>(row), ctc);
}
