// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef TableDowntimes_h
#define TableDowntimes_h

#include "config.h"

#include <map>
#include "Table.h"
#include "nagios.h"

class Downtime;
class TableHosts;
class TableContacts;
class TableServices;

using namespace std;

class TableDowntimes : public Table
{
   typedef map<unsigned long, Downtime *> _downtimes_t;
   _downtimes_t _downtimes;
public:
   TableDowntimes(TableHosts *, TableServices *, TableContacts *);
   const char *name() { return "downtimes"; };
   ~TableDowntimes();
   Downtime *findDowntime(unsigned long id);
   void add(nebstruct_downtime_data *);
   void answerQuery(Query *);
   _downtimes_t::iterator downtimesIteratorBegin() { return _downtimes.begin(); }
   _downtimes_t::iterator downtimesIteratorEnd() { return _downtimes.end(); }
};



#endif // TableDowntimes_h

