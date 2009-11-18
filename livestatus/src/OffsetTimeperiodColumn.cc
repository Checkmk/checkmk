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


#include "nagios.h"
#include <stdint.h>
#include "OffsetTimeperiodColumn.h"
#include "logger.h"


int32_t OffsetTimeperiodColumn::getValue(void *data)
{
   data = shiftPointer(data);
   if (!data)
      return 0;

   timeperiod *tp = *(timeperiod **)((char *)data + offset());

   if (!tp)
      return 1; // no timeperiod set -> Nagios assumes 7x24
   else if (inTimeperiod(tp))
      return 1;
   else
      return 0;
}

bool OffsetTimeperiodColumn::inTimeperiod(timeperiod *tp)
{
   time_t now = time(0);
   if (now != _cache_time) {
      _cache.clear();
      _cache_time = now;
   }

   _cache_t::iterator it = _cache.find(tp);
   if (it != _cache.end())
      return it->second;

   bool in = 0 == check_time_against_period(now, tp);
   _cache.insert(make_pair(tp, in));
   return in;
}

