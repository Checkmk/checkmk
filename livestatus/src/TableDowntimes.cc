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

#include "TableDowntimes.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "Downtime.h"
#include "logger.h"
#include "Query.h"
#include "OffsetStringColumn.h"
#include "OffsetIntColumn.h"

TableDowntimes::TableDowntimes(TableHosts *ht, TableServices *ts, TableContacts *tc)
{
   Downtime *ref = 0;
   addColumn(new OffsetStringColumn("author", 
	    "The contact that scheduled the downtime", (char *)&(ref->_author_name) - (char *)ref));
   addColumn(new OffsetStringColumn("comment", 
	    "A comment about the downtime", (char *)&(ref->_comment) - (char *)ref));
   addColumn(new OffsetIntColumn("id", 
	    "The id of the downtime", (char *)&(ref->_downtime_id) - (char *)ref));

   addColumn(new OffsetIntColumn("start_time",
	    "The start time of the downtime as UNIX timestamp", (char *)&(ref->_start_time) - (char *)ref));
   addColumn(new OffsetIntColumn("end_time",
	    "The end time of the downtime as UNIX timestamp", (char *)&(ref->_end_time) - (char *)ref));
   addColumn(new OffsetIntColumn("entry_time",
	    "The entry time of the downtime as UNIX timestamp", (char *)&(ref->_entry_time) - (char *)ref));
   
   addColumn(new OffsetIntColumn("type",
	    "The type of the downtime: 0 if it is active, 1 if it is pending", (char *)&(ref->_type) - (char *)ref));
   addColumn(new OffsetIntColumn("triggered_by",
	    "The id of the downtime this downtime was triggered by or 0 if it was not triggered by another downtime", 
	    (char *)&(ref->_triggered_by) - (char *)ref));
   addColumn(new OffsetIntColumn("fixed",
	    "A 1 if the downtime is fixed, a 0 if it is flexible", (char *)&(ref->_fixed) - (char *)ref));
   addColumn(new OffsetIntColumn("duration",
	    "The duration of the downtime in seconds", (char *)&(ref->_duration) - (char *)ref));

   ht->addColumns(this, "host_",    (char *)&(ref->_host)    - (char *)ref, tc, this);
   ts->addColumns(this, "service_", (char *)&(ref->_service) - (char *)ref, 0, tc, this);
}

TableDowntimes::~TableDowntimes()
{
   for (_downtimes_t::iterator it = _downtimes.begin();
	 it != _downtimes.end();
	 ++it)
   {
      delete it->second;
   }
}

void TableDowntimes::add(nebstruct_downtime_data *data)
{
   unsigned long id = data->downtime_id;
   if (data->type == NEBTYPE_DOWNTIME_ADD || data->type == NEBTYPE_DOWNTIME_LOAD) {
      // might be update -> delete previous data set
      _downtimes_t::iterator it = _downtimes.find(id);
      if (it != _downtimes.end()) {
	 delete it->second;
	 _downtimes.erase(it);
      }
      _downtimes.insert(make_pair(id, new Downtime(data)));
   }
   else if (data->type == NEBTYPE_DOWNTIME_DELETE) {
      _downtimes_t::iterator it = _downtimes.find(id);
      if (it == _downtimes.end())
	 logger(LG_INFO, "Cannot delete non-existing downtime %u", id);
      else {
	 delete it->second;
	 _downtimes.erase(it);
      }
   }
}

void TableDowntimes::answerQuery(Query *query)
{
   for (_downtimes_t::const_iterator it = _downtimes.begin();
	 it != _downtimes.end();
	 ++it)
   {
      if (!query->processDataset(it->second))
	 break;
   }
}

Downtime *TableDowntimes::findDowntime(unsigned long id)
{
   _downtimes_t::iterator it = _downtimes.find(id);
   if (it != _downtimes.end())
      return it->second;
   else
      return 0;
}

