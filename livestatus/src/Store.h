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

#ifndef Store_h
#define Store_h

#include "config.h"

#include "TableServices.h"
#include "TableHosts.h"
#include "TableHostgroups.h"
#include "TableServicegroups.h"
#include "TableContacts.h"
#include "TableCommands.h"
#include "TableDowntimes.h"
#include "TableStatus.h"
#include "TableColumns.h"
#include "OutputBuffer.h"
#include "InputBuffer.h"

class Store
{
  TableContacts      _table_contacts;
  TableCommands      _table_commands;
  TableHosts         _table_hosts;
  TableServices      _table_services;
  TableHostgroups    _table_hostgroups;
  TableServicegroups _table_servicegroups;
  TableDowntimes     _table_downtimes;
  TableStatus        _table_status;
  TableColumns       _table_columns;

  typedef map<string, Table *> _tables_t;
  _tables_t _tables;

public:
  Store();
  void registerHost(host *);
  void registerService(service *);
  void registerHostgroup(hostgroup *);
  void registerContact(contact *);
  void registerDowntime(nebstruct_downtime_data *);
  bool answerRequest(InputBuffer *, OutputBuffer *);

private:
  Table *findTable(string name);
  string readCommand(FILE *);
  void answerGetRequest(InputBuffer *, OutputBuffer *, const char *);
  void answerCommandRequest(const char *);
};

#endif // Store_h


