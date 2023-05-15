// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableServiceGroups.h"

#include <algorithm>
#include <memory>
#include <variant>  // IWYU pragma: keep
#include <vector>

#include "livestatus/Column.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/ServiceGroupMembersColumn.h"
#include "livestatus/ServiceListState.h"
#include "livestatus/StringColumn.h"
#include "livestatus/User.h"
namespace {
std::vector<::column::service_group_members::Entry> BuildServiceGroupListInfo(
    const IServiceGroup &sg, const User &user) {
    std::vector<::column::service_group_members::Entry> entries;
    sg.all([&user, &entries](const IService &s) {
        if (user.is_authorized_for_service(s)) {
            entries.emplace_back(s.host_name(), s.name(),
                                 static_cast<ServiceState>(s.current_state()),
                                 s.has_been_checked());
        }
        return true;
    });
    return entries;
}
}  // namespace

TableServiceGroups::TableServiceGroups(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{});
}

std::string TableServiceGroups::name() const { return "servicegroups"; }

std::string TableServiceGroups::namePrefix() const { return "servicegroup_"; }

// static
void TableServiceGroups::addColumns(Table *table, const std::string &prefix,
                                    const ColumnOffsets &offsets) {
    table->addColumn(std::make_unique<StringColumn<IServiceGroup>>(
        prefix + "name", "Name of the servicegroup", offsets,
        [](const IServiceGroup &r) { return r.name(); }));
    table->addColumn(std::make_unique<StringColumn<IServiceGroup>>(
        prefix + "alias", "An alias of the servicegroup", offsets,
        [](const IServiceGroup &r) { return r.alias(); }));
    table->addColumn(std::make_unique<StringColumn<IServiceGroup>>(
        prefix + "notes", "Optional additional notes about the service group",
        offsets, [](const IServiceGroup &r) { return r.notes(); }));
    table->addColumn(std::make_unique<StringColumn<IServiceGroup>>(
        prefix + "notes_url",
        "An optional URL to further notes on the service group", offsets,
        [](const IServiceGroup &r) { return r.notes_url(); }));
    table->addColumn(std::make_unique<StringColumn<IServiceGroup>>(
        prefix + "action_url",
        "An optional URL to custom notes or actions on the service group",
        offsets, [](const IServiceGroup &r) { return r.action_url(); }));
    table->addColumn(
        std::make_unique<ServiceGroupMembersColumn<
            IServiceGroup, ::column::service_group_members::Entry>>(
            prefix + "members",
            "A list of all members of the service group as host/service pairs",
            offsets,
            std::make_unique<ServiceGroupMembersRenderer>(
                ServiceGroupMembersRenderer::verbosity::none),
            [](const IServiceGroup &sg, const User &user) {
                return BuildServiceGroupListInfo(sg, user);
            }));
    table->addColumn(std::make_unique<ServiceGroupMembersColumn<
                         IServiceGroup,
                         ::column::service_group_members::Entry>>(
        prefix + "members_with_state",
        "A list of all members of the service group with state and has_been_checked",
        offsets,
        std::make_unique<ServiceGroupMembersRenderer>(
            ServiceGroupMembersRenderer::verbosity::full),
        [](const IServiceGroup &sg, const User &user) {
            return BuildServiceGroupListInfo(sg, user);
        }));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "worst_service_state",
        "The worst soft state of all of the groups services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets, ServiceListState{ServiceListState::Type::worst_state}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services", "The total number of services in the group",
        offsets, ServiceListState{ServiceListState::Type::num}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_ok",
        "The number of services in the group that are OK", offsets,
        ServiceListState{ServiceListState::Type::num_ok}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_warn",
        "The number of services in the group that are WARN", offsets,
        ServiceListState{ServiceListState::Type::num_warn}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_crit",
        "The number of services in the group that are CRIT", offsets,
        ServiceListState{ServiceListState::Type::num_crit}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_unknown",
        "The number of services in the group that are UNKNOWN", offsets,
        ServiceListState{ServiceListState::Type::num_unknown}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_pending",
        "The number of services in the group that are PENDING", offsets,
        ServiceListState{ServiceListState::Type::num_pending}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_handled_problems",
        "The number of services in the group that have handled problems",
        offsets,
        ServiceListState{ServiceListState::Type::num_handled_problems}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_unhandled_problems",
        "The number of services in the group that have unhandled problems",
        offsets,
        ServiceListState{ServiceListState::Type::num_unhandled_problems}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_hard_ok",
        "The number of services in the group that are OK", offsets,
        ServiceListState{ServiceListState::Type::num_hard_ok}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_hard_warn",
        "The number of services in the group that are WARN", offsets,
        ServiceListState{ServiceListState::Type::num_hard_warn}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_hard_crit",
        "The number of services in the group that are CRIT", offsets,
        ServiceListState{ServiceListState::Type::num_hard_crit}));
    table->addColumn(std::make_unique<IntColumn<IServiceGroup>>(
        prefix + "num_services_hard_unknown",
        "The number of services in the group that are UNKNOWN", offsets,
        ServiceListState{ServiceListState::Type::num_hard_unknown}));
}

void TableServiceGroups::answerQuery(Query &query, const User &user) {
    auto process = [&](const IServiceGroup &group) {
        return !user.is_authorized_for_service_group(group) ||
               query.processDataset(Row{&group});
    };

    core()->all_of_service_groups(
        [&process](const IServiceGroup &r) { return process(r); });
}

Row TableServiceGroups::get(const std::string &primary_key) const {
    // "name" is the primary key
    return Row{core()->find_servicegroup(primary_key)};
}
