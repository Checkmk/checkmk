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

#include <string.h>
#include <ctype.h>

#include "strutil.h"

void rstrip(char *c)
{
   char *w = c + strlen(c) - 1;
   while (w >= c && isspace(*w))
      *w-- = '\0';
}

char *lstrip(char *c)
{
   return (char *)lstrip((const char *)c);
}

const char *lstrip(const char *c)
{
   while (isspace(*c)) c++;
   return c;
}

/* *c points to a string containing
   white space separated columns. This method returns
   a pointer to the zero-terminated next field. That
   might be identical with *c itself. The pointer c
   is then moved to the possible beginning of the
   next field. */
char *next_field(char **c)
{
   /* *c points to first character of field */
   char *begin = lstrip(*c); // skip leading spaces
   if (!*begin) {
      *c = begin;
      return 0; // found end of string -> no more field
   }

   char *end = begin; // copy pointer, search end of field
   while (*end && !isspace(*end)) end++;  // search for \0 or white space
   if (*end) { // string continues -> terminate field with '\0'
      *end = '\0';
      *c = end + 1; // skip to character right *after* '\0'
   }
   else
      *c = end; // no more field, point to '\0'
   return begin;
}

