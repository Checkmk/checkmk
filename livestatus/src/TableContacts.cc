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
#include "OffsetIntColumn.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "TimeperiodColumn.h"
#include "nagios.h"

using std::make_unique;
using std::string;
using std::to_string;

extern contact *contact_list;

TableContacts::TableContacts(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", -1);
}

string TableContacts::name() const { return "contacts"; }

string TableContacts::namePrefix() const { return "contact_"; }

// static
void TableContacts::addColumns(Table *table, const string &prefix,
                               int indirect_offset) {
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "name", "The login name of the contact person",
        DANGEROUS_OFFSETOF(contact, name), indirect_offset, -1, -1));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "alias", "The full name of the contact",
        DANGEROUS_OFFSETOF(contact, alias), indirect_offset, -1, -1));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "email", "The email address of the contact",
        DANGEROUS_OFFSETOF(contact, email), indirect_offset, -1, -1));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "pager", "The pager address of the contact",
        DANGEROUS_OFFSETOF(contact, pager), indirect_offset, -1, -1));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "host_notification_period",
        "The time period in which the contact will be notified about host problems",
        DANGEROUS_OFFSETOF(contact, host_notification_period), indirect_offset,
        -1, -1));
    table->addColumn(make_unique<OffsetStringColumn>(
        prefix + "service_notification_period",
        "The time period in which the contact will be notified about service problems",
        DANGEROUS_OFFSETOF(contact, service_notification_period),
        indirect_offset, -1, -1));
    for (int i = 1; i <= MAX_CONTACT_ADDRESSES; ++i) {
        string b = "address" + to_string(i);
        table->addColumn(make_unique<OffsetStringColumn>(
            prefix + b, "The additional field " + b,
            DANGEROUS_OFFSETOF(contact, address[i]), indirect_offset, -1, -1));
    }

    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "can_submit_commands",
        "Wether the contact is allowed to submit commands (0/1)",
        DANGEROUS_OFFSETOF(contact, can_submit_commands), indirect_offset, -1,
        -1));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "host_notifications_enabled",
        "Wether the contact will be notified about host problems in general (0/1)",
        DANGEROUS_OFFSETOF(contact, host_notifications_enabled),
        indirect_offset, -1, -1));
    table->addColumn(make_unique<OffsetIntColumn>(
        prefix + "service_notifications_enabled",
        "Wether the contact will be notified about service problems in general (0/1)",
        DANGEROUS_OFFSETOF(contact, service_notifications_enabled),
        indirect_offset, -1, -1));

    table->addColumn(make_unique<TimeperiodColumn>(
        prefix + "in_host_notification_period",
        "Wether the contact is currently in his/her host notification period (0/1)",
        indirect_offset,
        DANGEROUS_OFFSETOF(contact, host_notification_period_ptr), -1));
    table->addColumn(make_unique<TimeperiodColumn>(
        prefix + "in_service_notification_period",
        "Wether the contact is currently in his/her service notification period (0/1)",
        indirect_offset,
        DANGEROUS_OFFSETOF(contact, service_notification_period_ptr), -1));

    table->addColumn(make_unique<CustomVarsNamesColumn>(
        prefix + "custom_variable_names",
        "A list of all custom variables of the contact",
        DANGEROUS_OFFSETOF(contact, custom_variables), indirect_offset, -1,
        -1));
    table->addColumn(make_unique<CustomVarsValuesColumn>(
        prefix + "custom_variable_values",
        "A list of the values of all custom variables of the contact",
        DANGEROUS_OFFSETOF(contact, custom_variables), indirect_offset, -1,
        -1));
    table->addColumn(make_unique<CustomVarsDictColumn>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        DANGEROUS_OFFSETOF(contact, custom_variables), indirect_offset, -1,
        -1));
    table->addColumn(make_unique<AttributeListAsIntColumn>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        DANGEROUS_OFFSETOF(contact, modified_attributes), indirect_offset, -1,
        -1));
    table->addColumn(make_unique<AttributeListColumn>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes",
        DANGEROUS_OFFSETOF(contact, modified_attributes), indirect_offset, -1,
        -1));
}

void TableContacts::answerQuery(Query *query) {
    for (contact *ct = contact_list; ct != nullptr; ct = ct->next) {
        if (!query->processDataset(Row(ct))) {
            break;
        }
    }
}

Row TableContacts::findObject(const string &objectspec) const {
    return Row(find_contact(const_cast<char *>(objectspec.c_str())));
}
