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

#include "Store.h"
#include "Query.h"
#include "logger.h"
#include "strutil.h"
#include "OutputBuffer.h"

Store::Store()
   : _table_hosts(&_table_contacts, &_table_downtimes)
   , _table_services(&_table_hosts, &_table_contacts, &_table_downtimes)
     , _table_downtimes(&_table_hosts, &_table_services, &_table_contacts)
{
   _tables.insert(make_pair("hosts", &_table_hosts));
   _tables.insert(make_pair("services", &_table_services));
   _tables.insert(make_pair("hostgroups", &_table_hostgroups));
   _tables.insert(make_pair("servicegroups", &_table_servicegroups));
   _tables.insert(make_pair("contacts", &_table_contacts));
   _tables.insert(make_pair("commands", &_table_commands));
   _tables.insert(make_pair("downtimes", &_table_downtimes));
   _tables.insert(make_pair("status", &_table_status));
   _tables.insert(make_pair("columns", &_table_columns));

   for (_tables_t::iterator it = _tables.begin();
	 it != _tables.end();
	 ++it)
   {
      _table_columns.addTable(it->second);
   }
}

Table *Store::findTable(string name)
{
   _tables_t::iterator it = _tables.find(name);
   if (it == _tables.end())
      return 0;
   else
      return it->second;
}

void Store::registerHost(host *h)
{
   _table_hosts.add(h);
}

void Store::registerService(service *s)
{
   _table_services.add(s);
}

void Store::registerContact(contact *s)
{
   _table_contacts.add(s);
}

void Store::registerDowntime(nebstruct_downtime_data *d)
{
   _table_downtimes.add(d);
}

string Store::readCommand(FILE *c)
{
   char command[512];
   if (0 == fgets(command, sizeof(command), c))
      return "";
   if (strncmp(command, "GET ", 4))
      return "";
   rstrip(command + 4);
   return command + 4;
}

bool Store::answerRequest(InputBuffer *input, OutputBuffer *output)
{
   output->reset();
   int r = input->readRequest();
   if (r != IB_REQUEST_READ) {
      output->setError(RESPONSE_CODE_INCOMPLETE_REQUEST, "Couldn't read complete request");
      return false;
   }
   string l = input->nextLine();
   const char *line = l.c_str();
   if (!strncmp(line, "GET ", 4))
      answerGetRequest(input, output, lstrip(line + 4));
   else if (!strncmp(line, "COMMAND ", 8))
      answerCommandRequest(lstrip(line + 8));
   else 
      output->setError(RESPONSE_CODE_INVALID_REQUEST, "Invalid request method");
   return output->doKeepalive();
}

void Store::answerCommandRequest(const char *command)
{
   int buffer_items = -1;
   int ret = submit_external_command((char *)command, &buffer_items);
}


void Store::answerGetRequest(InputBuffer *input, OutputBuffer *output, const char *tablename)
{
   output->reset();

   if (!tablename[0]) {
      output->setError(RESPONSE_CODE_INVALID_REQUEST, "Invalid GET request, missing tablename");
   }
   Table *table = findTable(tablename);
   if (!table) {
      output->setError(RESPONSE_CODE_NOT_FOUND, "Invalid GET request, no such table '%s'", tablename);
   }
   Query query(input, output, table);

   if (table) {
      if (query.hasNoColumns()) {
	 table->addAllColumnsToQuery(&query);
	 query.setShowColumnHeaders(true);
      }
      struct timeval before, after;
      gettimeofday(&before, 0);
      query.start();
      table->answerQuery(&query);
      query.finish();
      gettimeofday(&after, 0);
      unsigned long ustime = (after.tv_sec - before.tv_sec) * 1000000 + (after.tv_usec - before.tv_usec);
      logger(LG_INFO, "Time to process request: %lu us. Size of answer: %d bytes", ustime, output->size());
   }
}


