// +------------------------------------------------------------------+
// |                     _           _           _                    |
// |                  __| |_  ___ __| |__  _ __ | |__                 |
// |                 / _| ' \/ -_) _| / / | '  \| / /                 |
// |                 \__|_||_\___\__|_\_\_|_|_|_|_\_\                 |
// |                                   |___|                          |
// |              _   _   __  _         _        _ ____               |
// |             / | / | /  \| |__  ___| |_ __ _/ |__  |              |
// |             | |_| || () | '_ \/ -_)  _/ _` | | / /               |
// |             |_(_)_(_)__/|_.__/\___|\__\__,_|_|/_/                |
// |                                            check_mk 1.1.0beta17  |
// |                                                                  |
// | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
// 
// This file is part of check_mk 1.1.0beta17.
// The official homepage is at http://mathias-kettner.de/check_mk.
// 
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#define NSCORE
#include "nagios/objects.h"
#include "TableContacts.h"
#include "Query.h"
#include "OffsetStringColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetTimeperiodColumn.h"
#include "CustomVarsColumn.h"


TableContacts::TableContacts()
{
   addColumns(this, "", -1);
}

void TableContacts::addColumns(Table *table, string prefix, int indirect_offset)
{
   contact ctc;
   char *ref = (char *)&ctc;
   table->addColumn(new OffsetStringColumn(prefix + "name", 
	    "The login name of the contact person", (char *)(&ctc.name) - ref, indirect_offset));
   table->addColumn(new OffsetStringColumn(prefix + "alias", 
	    "The full name of the contact", (char *)(&ctc.alias) - ref, indirect_offset));
   table->addColumn(new OffsetStringColumn(prefix + "email", 
	    "The email address of the contact", (char *)(&ctc.email) - ref, indirect_offset));
   table->addColumn(new OffsetStringColumn(prefix + "pager", 
	    "The pager address of the contact", (char *)(&ctc.pager) - ref, indirect_offset));
   table->addColumn(new OffsetStringColumn(prefix + "host_notification_period", 
	    "The time period in which the contact will be notified about host problems", (char *)(&ctc.host_notification_period) - ref, indirect_offset));
   table->addColumn(new OffsetStringColumn(prefix + "service_notification_period", 
	    "The time period in which the contact will be notified about service problems", (char *)(&ctc.service_notification_period) - ref, indirect_offset));
   for (int i=0; i<MAX_CONTACT_ADDRESSES; i++) {
      char b[32];
      snprintf(b, sizeof(b), "address%d", i+1);
      table->addColumn(new OffsetStringColumn(prefix + b, 
	       (string("The additional field ") + b), (char *)(&ctc.address[i]) - ref, indirect_offset));
   }

   table->addColumn(new OffsetIntColumn("can_submit_commands", 
	    "Wether the contact is allowed to submit commands (0/1)", (char *)&ctc.can_submit_commands - ref, indirect_offset));
   table->addColumn(new OffsetIntColumn("host_notifications_enabled", 
	    "Wether the contact will be notified about host problems in general (0/1)", (char *)&ctc.host_notifications_enabled - ref, indirect_offset));
   table->addColumn(new OffsetIntColumn("service_notifications_enabled", 
	    "Wether the contact will be notified about service problems in general (0/1)", (char *)&ctc.service_notifications_enabled - ref, indirect_offset));

   table->addColumn(new OffsetTimeperiodColumn("in_host_notification_period", 
	    "Wether the contact is currently in his/her host notification period (0/1)", (char *)&ctc.host_notification_period_ptr - ref, indirect_offset));
   table->addColumn(new OffsetTimeperiodColumn("in_service_notification_period", 
	    "Wether the contact is currently in his/her service notification period (0/1)", (char *)&ctc.service_notification_period_ptr - ref, indirect_offset));
   
   table->addColumn(new CustomVarsColumn(prefix + "custom_variable_names", 
	    "A list of all custom variables of the contact", (char *)(&ctc.custom_variables) - ref, indirect_offset, CVT_VARNAMES));
   table->addColumn(new CustomVarsColumn(prefix + "custom_variable_values", 
	    "A list of the values of all custom variables of the contact", (char *)(&ctc.custom_variables) - ref, indirect_offset, CVT_VALUES));
}

void TableContacts::add(contact *ctc)
{
   _contacts.insert(ctc);
}

void TableContacts::answerQuery(Query *query)
{
   for (_contacts_t::const_iterator it = _contacts.begin();
	 it != _contacts.end();
	 ++it)
   {
      if (!query->processDataset(*it))
	 break;
   }
}
