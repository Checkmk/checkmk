// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableContacts.h"
#include <memory>
#include "AttributeListAsIntColumn.h"
#include "AttributeListColumn.h"
#include "Column.h"
#include "CustomVarsDictColumn.h"
#include "CustomVarsNamesColumn.h"
#include "CustomVarsValuesColumn.h"
#include "MonitoringCore.h"
#include "OffsetIntColumn.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "TimeperiodColumn.h"
#include "nagios.h"

extern contact *contact_list;

TableContacts::TableContacts(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", -1);
}

std::string TableContacts::name() const { return "contacts"; }

std::string TableContacts::namePrefix() const { return "contact_"; }

// static
void TableContacts::addColumns(Table *table, const std::string &prefix,
                               int indirect_offset) {
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "name", "The login name of the contact person",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, name)}));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "alias", "The full name of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, alias)}));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "email", "The email address of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, email)}));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "pager", "The pager address of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, pager)}));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "host_notification_period",
        "The time period in which the contact will be notified about host problems",
        Column::Offsets{
            indirect_offset, -1, -1,
            DANGEROUS_OFFSETOF(contact, host_notification_period)}));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "service_notification_period",
        "The time period in which the contact will be notified about service problems",
        Column::Offsets{
            indirect_offset, -1, -1,
            DANGEROUS_OFFSETOF(contact, service_notification_period)}));
    for (int i = 0; i < MAX_CONTACT_ADDRESSES; ++i) {
        std::string b = "address" + std::to_string(i + 1);
        table->addColumn(std::make_unique<OffsetStringColumn>(
            prefix + b, "The additional field " + b,
            Column::Offsets{indirect_offset, -1, -1,
                            DANGEROUS_OFFSETOF(contact, address[i])}));
    }

    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "can_submit_commands",
        "Wether the contact is allowed to submit commands (0/1)",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, can_submit_commands)}));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "host_notifications_enabled",
        "Wether the contact will be notified about host problems in general (0/1)",
        Column::Offsets{
            indirect_offset, -1, -1,
            DANGEROUS_OFFSETOF(contact, host_notifications_enabled)}));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "service_notifications_enabled",
        "Wether the contact will be notified about service problems in general (0/1)",
        Column::Offsets{
            indirect_offset, -1, -1,
            DANGEROUS_OFFSETOF(contact, service_notifications_enabled)}));

    table->addColumn(std::make_unique<TimeperiodColumn>(
        prefix + "in_host_notification_period",
        "Wether the contact is currently in his/her host notification period (0/1)",
        Column::Offsets{
            indirect_offset,
            DANGEROUS_OFFSETOF(contact, host_notification_period_ptr), -1, 0}));
    table->addColumn(std::make_unique<TimeperiodColumn>(
        prefix + "in_service_notification_period",
        "Wether the contact is currently in his/her service notification period (0/1)",
        Column::Offsets{
            indirect_offset,
            DANGEROUS_OFFSETOF(contact, service_notification_period_ptr), -1,
            0}));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "custom_variable_names",
        "A list of all custom variables of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "custom_variable_values",
        "A list of the values of all custom variables of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::custom_variables));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "tag_names", "A list of all tags of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "tag_values",
        "A list of the values of all tags of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "tags", "A dictionary of the tags",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::tags));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_names", "A list of all labels of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_values",
        "A list of the values of all labels of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "labels", "A dictionary of the labels",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::labels));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_source_names", "A list of all sources of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_source_values",
        "A list of the values of all sources of the contact",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "label_sources", "A dictionary of the label sources",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, custom_variables)},
        table->core(), AttributeKind::label_sources));

    table->addColumn(std::make_unique<AttributeListAsIntColumn>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, modified_attributes)}));
    table->addColumn(std::make_unique<AttributeListColumn>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes",
        Column::Offsets{indirect_offset, -1, -1,
                        DANGEROUS_OFFSETOF(contact, modified_attributes)}));
}

void TableContacts::answerQuery(Query *query) {
    for (contact *ct = contact_list; ct != nullptr; ct = ct->next) {
        if (!query->processDataset(Row(ct))) {
            break;
        }
    }
}

Row TableContacts::findObject(const std::string &objectspec) const {
    return Row(core()->find_contact(objectspec));
}
