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

#include "DowntimesColumn.h"
#include "Downtime.h"
#include "TableDowntimes.h"
#include "logger.h"
#include "Query.h"

void DowntimesColumn::output(void *data, Query *query)
{
   query->outputBeginList();
   data = shiftPointer(data); // points to host or service
   if (data) 
   {
      bool first = true;

      for (map<unsigned long, Downtime *>::iterator it = _table_downtimes->downtimesIteratorBegin();
	    it != _table_downtimes->downtimesIteratorEnd();
	    ++it)
      {
	 unsigned long id = it->first;
	 Downtime *dt = it->second;
	 if ((void *)dt->_service == data ||
	       (dt->_service == 0 && dt->_host == data))
	 {
	    if (first)
	       first = false;
	    else
	       query->outputListSeparator();
	    query->outputUnsignedLong(id);
	 }
      }
   }
   query->outputEndList();
}

void *DowntimesColumn::getNagiosObject(char *name)
{
   unsigned int id = strtoul(name, 0, 10);
   return (void *)id; // Hack. Convert number into pointer.
}

bool DowntimesColumn::isNagiosMember(void *data, void *member)
{
   // data points to a host or service
   // member is not a pointer, but an unsigned int (hack)
   int64_t id = (int64_t)member; // Hack. Convert it back.
   Downtime *dt = _table_downtimes->findDowntime(id);
   return dt != 0 && \
		(	 dt->_service == (service *)data
			 || (dt->_service == 0 && dt->_host == (host *)data));
}
