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

#include "logger.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

void logger(int priority, const char *loginfo, ...)
{
   char buffer[8192];
   snprintf(buffer, 20, "livestatus: ");

   va_list ap;
   va_start(ap, loginfo);
   vsnprintf(buffer + strlen(buffer), sizeof(buffer) - strlen(buffer), loginfo, ap);
   va_end(ap);
   write_to_all_logs(buffer, priority);

   /* DEBUGING
      FILE *x = fopen("/tmp/hirn.log", "a+");
      va_start(ap, loginfo);
      vfprintf(x, loginfo, ap);
      fputc('\n', x);
      va_end(ap);
      fclose(x);
    */
}


