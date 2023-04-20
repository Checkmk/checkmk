// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableContacts.h"

#include <cstdint>
#include <memory>
#include <unordered_map>
#include <variant>  // IWYU pragma: keep
#include <vector>

#include "livestatus/AttributeBitmaskColumn.h"
#include "livestatus/AttributeListColumn.h"
#include "livestatus/Column.h"
#include "livestatus/DictColumn.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/ListColumn.h"
#include "livestatus/MapUtils.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/StringColumn.h"

// identical to MAX_CONTACT_ADDRESSES from nagios
constexpr int32_t max_contact_addresses = 6;

TableContacts::TableContacts(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{});
}

std::string TableContacts::name() const { return "contacts"; }

std::string TableContacts::namePrefix() const { return "contact_"; }

// static
void TableContacts::addColumns(Table *table, const std::string &prefix,
                               const ColumnOffsets &offsets) {
    table->addColumn(std::make_unique<StringColumn<IContact>>(
        prefix + "name", "The login name of the contact person", offsets,
        [](const IContact &ct) { return ct.name(); }));
    table->addColumn(std::make_unique<StringColumn<IContact>>(
        prefix + "alias", "The full name of the contact", offsets,
        [](const IContact &ct) { return ct.alias(); }));
    table->addColumn(std::make_unique<StringColumn<IContact>>(
        prefix + "email", "The email address of the contact", offsets,
        [](const IContact &ct) { return ct.email(); }));
    table->addColumn(std::make_unique<StringColumn<IContact>>(
        prefix + "pager", "The pager address of the contact", offsets,
        [](const IContact &ct) { return ct.pager(); }));
    table->addColumn(std::make_unique<StringColumn<IContact>>(
        prefix + "host_notification_period",
        "The time period in which the contact will be notified about host problems",
        offsets,
        [](const IContact &ct) { return ct.hostNotificationPeriod(); }));
    table->addColumn(std::make_unique<StringColumn<IContact>>(
        prefix + "service_notification_period",
        "The time period in which the contact will be notified about service problems",
        offsets,
        [](const IContact &ct) { return ct.serviceNotificationPeriod(); }));
    for (int i = 0; i < max_contact_addresses; ++i) {
        const std::string b = "address" + std::to_string(i + 1);
        table->addColumn(std::make_unique<StringColumn<IContact>>(
            prefix + b, "The additional field " + b, offsets,
            [i](const IContact &ct) { return ct.address(i); }));
    }

    table->addColumn(std::make_unique<BoolColumn<IContact>>(
        prefix + "can_submit_commands",
        "Wether the contact is allowed to submit commands (0/1)", offsets,
        [](const IContact &ct) { return ct.canSubmitCommands(); }));
    table->addColumn(std::make_unique<BoolColumn<IContact>>(
        prefix + "host_notifications_enabled",
        "Wether the contact will be notified about host problems in general (0/1)",
        offsets,
        [](const IContact &ct) { return ct.isHostNotificationsEnabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IContact>>(
        prefix + "service_notifications_enabled",
        "Wether the contact will be notified about service problems in general (0/1)",
        offsets,
        [](const IContact &ct) { return ct.isServiceNotificationsEnabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IContact>>(
        prefix + "in_host_notification_period",
        "Wether the contact is currently in his/her host notification period (0/1)",
        offsets,
        [](const IContact &ct) { return ct.isInHostNotificationPeriod(); }));
    table->addColumn(std::make_unique<BoolColumn<IContact>>(
        prefix + "in_service_notification_period",
        "Wether the contact is currently in his/her service notification period (0/1)",
        offsets,
        [](const IContact &ct) { return ct.isInServiceNotificationPeriod(); }));
    table->addColumn(std::make_unique<ListColumn<IContact>>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", offsets,
        [](const IContact &ct) { return mk::map_keys(ct.customVariables()); }));
    table->addColumn(std::make_unique<ListColumn<IContact>>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables", offsets,
        [](const IContact &ct) {
            return mk::map_values(ct.customVariables());
        }));
    table->addColumn(std::make_unique<DictColumn<IContact>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets, [](const IContact &ct) { return ct.customVariables(); }));

    table->addColumn(std::make_unique<ListColumn<IContact>>(
        prefix + "tag_names", "A list of the names of the tags", offsets,
        [](const IContact &ct) { return mk::map_keys(ct.tags()); }));
    table->addColumn(std::make_unique<ListColumn<IContact>>(
        prefix + "tag_values", "A list of the values of the tags", offsets,
        [](const IContact &ct) { return mk::map_values(ct.tags()); }));
    table->addColumn(std::make_unique<DictColumn<IContact>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        [](const IContact &ct) { return ct.tags(); }));

    table->addColumn(std::make_unique<ListColumn<IContact>>(
        prefix + "label_names", "A list of the names of the labels", offsets,
        [](const IContact &ct) { return mk::map_keys(ct.labels()); }));
    table->addColumn(std::make_unique<ListColumn<IContact>>(
        prefix + "label_values", "A list of the values of the labels", offsets,
        [](const IContact &ct) { return mk::map_values(ct.labels()); }));
    table->addColumn(std::make_unique<DictColumn<IContact>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        [](const IContact &ct) { return ct.labels(); }));

    table->addColumn(std::make_unique<ListColumn<IContact>>(
        prefix + "label_source_names",
        "A list of the names of the label sources", offsets,
        [](const IContact &ct) { return mk::map_keys(ct.labelSources()); }));
    table->addColumn(std::make_unique<ListColumn<IContact>>(
        prefix + "label_source_values",
        "A list of the values of the label sources", offsets,
        [](const IContact &ct) { return mk::map_values(ct.labelSources()); }));
    table->addColumn(std::make_unique<DictColumn<IContact>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        [](const IContact &ct) { return ct.labelSources(); }));

    table->addColumn(std::make_unique<AttributeBitmaskColumn<IContact>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const IContact &ct) { return ct.modifiedAttributes(); }));
    table->addColumn(std::make_unique<AttributeListColumn<
                         IContact, column::attribute_list::AttributeBit>>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets, [](const IContact &ct) {
            return column::attribute_list::encode(ct.modifiedAttributes());
        }));
}

void TableContacts::answerQuery(Query &query, const User & /*user*/) {
    core()->all_of_contacts(
        [&query](const IContact &r) { return query.processDataset(Row{&r}); });
}

Row TableContacts::get(const std::string &primary_key) const {
    // "name" is the primary key
    return Row{core()->find_contact(primary_key)};
}
