// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableContacts.h"

#include <cstdint>
#include <functional>
#include <memory>
#include <unordered_map>
#include <vector>

#include "livestatus/AttributeBitmaskColumn.h"
#include "livestatus/AttributeListColumn.h"
#include "livestatus/Column.h"
#include "livestatus/DictColumn.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/ListColumn.h"
#include "livestatus/MapUtils.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"

using row_type = IContact;

// identical to MAX_CONTACT_ADDRESSES from nagios
constexpr int32_t max_contact_addresses = 6;

TableContacts::TableContacts() { addColumns(this, "", ColumnOffsets{}); }

std::string TableContacts::name() const { return "contacts"; }

std::string TableContacts::namePrefix() const { return "contact_"; }

// static
void TableContacts::addColumns(Table *table, const std::string &prefix,
                               const ColumnOffsets &offsets) {
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "name", "The login name of the contact person", offsets,
        [](const row_type &row) { return row.name(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "alias", "The full name of the contact", offsets,
        [](const row_type &row) { return row.alias(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "email", "The email address of the contact", offsets,
        [](const row_type &row) { return row.email(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "pager", "The pager address of the contact", offsets,
        [](const row_type &row) { return row.pager(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "host_notification_period",
        "The time period in which the contact will be notified about host problems",
        offsets,
        [](const row_type &row) { return row.hostNotificationPeriod(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "service_notification_period",
        "The time period in which the contact will be notified about service problems",
        offsets,
        [](const row_type &row) { return row.serviceNotificationPeriod(); }));
    for (int i = 0; i < max_contact_addresses; ++i) {
        const std::string b = "address" + std::to_string(i + 1);
        table->addColumn(std::make_unique<StringColumn<row_type>>(
            prefix + b, "The additional field " + b, offsets,
            [i](const row_type &row) { return row.address(i); }));
    }

    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "can_submit_commands",
        "Wether the contact is allowed to submit commands (0/1)", offsets,
        [](const row_type &row) { return row.canSubmitCommands(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "host_notifications_enabled",
        "Wether the contact will be notified about host problems in general (0/1)",
        offsets,
        [](const row_type &row) { return row.isHostNotificationsEnabled(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "service_notifications_enabled",
        "Wether the contact will be notified about service problems in general (0/1)",
        offsets, [](const row_type &row) {
            return row.isServiceNotificationsEnabled();
        }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "in_host_notification_period",
        "Wether the contact is currently in his/her host notification period (0/1)",
        offsets,
        [](const row_type &row) { return row.isInHostNotificationPeriod(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "in_service_notification_period",
        "Wether the contact is currently in his/her service notification period (0/1)",
        offsets, [](const row_type &row) {
            return row.isInServiceNotificationPeriod();
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", offsets,
        [](const row_type &row) {
            return mk::map_keys(row.customVariables());
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables", offsets,
        [](const row_type &row) {
            return mk::map_values(row.customVariables());
        }));
    table->addColumn(std::make_unique<DictStrValueColumn<row_type>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets, [](const row_type &row) { return row.customVariables(); }));

    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "tag_names", "A list of the names of the tags", offsets,
        [](const row_type &row) { return mk::map_keys(row.tags()); }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "tag_values", "A list of the values of the tags", offsets,
        [](const row_type &row) { return mk::map_values(row.tags()); }));
    table->addColumn(std::make_unique<DictStrValueColumn<row_type>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        [](const row_type &row) { return row.tags(); }));

    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "label_names", "A list of the names of the labels", offsets,
        [](const row_type &row) { return mk::map_keys(row.labels()); }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "label_values", "A list of the values of the labels", offsets,
        [](const row_type &row) { return mk::map_values(row.labels()); }));
    table->addColumn(std::make_unique<DictStrValueColumn<row_type>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        [](const row_type &row) { return row.labels(); }));

    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "label_source_names",
        "A list of the names of the label sources", offsets,
        [](const row_type &row) { return mk::map_keys(row.labelSources()); }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "label_source_values",
        "A list of the values of the label sources", offsets,
        [](const row_type &row) {
            return mk::map_values(row.labelSources());
        }));
    table->addColumn(std::make_unique<DictStrValueColumn<row_type>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        [](const row_type &row) { return row.labelSources(); }));

    table->addColumn(std::make_unique<AttributeBitmaskColumn<row_type>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const row_type &row) { return row.modifiedAttributes(); }));
    table->addColumn(std::make_unique<AttributeListColumn<
                         row_type, column::attribute_list::AttributeBit>>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets, [](const row_type &row) {
            return column::attribute_list::encode(row.modifiedAttributes());
        }));
}

void TableContacts::answerQuery(Query &query, const User & /*user*/,
                                const ICore &core) {
    core.all_of_contacts([&query](const row_type &row) {
        return query.processDataset(Row{&row});
    });
}

Row TableContacts::get(const std::string &primary_key,
                       const ICore &core) const {
    // "name" is the primary key
    return Row{core.find_contact(primary_key)};
}
