// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

#include "ServicelistColumn.h"
#include "ServicelistColumnFilter.h"
#include "nagios.h"
#include "Query.h"

servicesmember *ServicelistColumn::getMembers(void *data)
{
   data = shiftPointer(data);
   if (!data) return 0;

   return *(servicesmember **)((char *)data + _offset);
}

void ServicelistColumn::output(void *data, Query *query)
{
   query->outputBeginList();
   servicesmember *mem = getMembers(data);

   bool first = true;
   while (mem) {
      if (!first)
	 query->outputListSeparator();
      else
	 first = false;
      query->outputHostService(mem->host_name, mem->service_description);
      mem = mem->next;
   }
   query->outputEndList();
}

Filter *ServicelistColumn::createFilter(int opid, char *value)
{
  return new ServicelistColumnFilter(this, opid, value);
}

