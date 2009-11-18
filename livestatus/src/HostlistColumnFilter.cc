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

#include "HostlistColumnFilter.h"
#include "HostlistColumn.h"
#include "nagios.h"
#include "opids.h"
#include "logger.h"

bool HostlistColumnFilter::accepts(void *data)
{
   // data points to a primary data object. We need to extract
   // a pointer to a host list
   hostsmember *mem = _hostlist_column->getMembers(data);

   // test for empty list
   if (abs(_opid) == OP_EQUAL && _ref_value == "")
      return (mem == 0) == (_opid == OP_EQUAL);

   bool is_member = false;
   while (mem) {
      char *host_name = mem->host_name;
      if (!host_name)
	 host_name = mem->host_ptr->name;
      
      if (host_name == _ref_value) {
	 return true;
	 break;
      }
      mem = mem->next;
   }
   switch (_opid) {
      case -OP_LESS: /* !< means >= means 'contains' */
	 return is_member;
      case OP_LESS:
	 return !is_member;
      default:
	 logger(LG_INFO, "Sorry, Operator %d for host lists lists not implemented.", _opid);
	 return true;
   }
}

