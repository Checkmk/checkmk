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

#include "ServicelistStateColumn.h"
#include "nagios.h"

// return true if state1 is worse than state2
bool ServicelistStateColumn::svcStateIsWorse(int32_t state1, int32_t state2)
{
   if (state1 == 0) return false;        // OK is worse than nothing
   else if (state2 == 0) return true;    // everything else is worse then OK
   else if (state2 == 2) return false;   // nothing is worse than CRIT
   else if (state1 == 2) return true;    // state1 is CRIT, state2 not
   else return (state1 > state2);        // both or WARN or UNKNOWN
}

servicesmember *ServicelistStateColumn::getMembers(void *data)
{
   data = shiftPointer(data);
   if (!data) return 0;

   return *(servicesmember **)((char *)data + _offset);
}

int32_t ServicelistStateColumn::getValue(int logictype, servicesmember *mem)
{
   int32_t result = 0;

   while (mem) {
      service *svc = mem->service_ptr;
      int state;
      if (logictype >= 60) {
	 state = svc->last_hard_state;
         logictype -= 64;
      }
      else
	 state = svc->current_state;

      switch (logictype) {
	 case SLSC_WORST_STATE: 
	    if (svcStateIsWorse(result, state)) result = state; 
	    break;
	 case SLSC_NUM: 
	    result++; 
   	    break;
	 default: 
	    if (state == logictype) 
	       result++; 
	    break;
      }
      mem = mem->next;
   }
   return result;
}


int32_t ServicelistStateColumn::getValue(void *data)
{
   servicesmember *mem = getMembers(data);
   return getValue(_logictype, mem);
}

