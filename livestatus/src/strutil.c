// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

#include <string.h>
#include <ctype.h>

#include "strutil.h"

char *rstrip(char *c)
{
    char *w = c + strlen(c) - 1;
    while (w >= c && isspace(*w))
        *w-- = '\0';
    return c;
}

char *lstrip(char *c)
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

/* similar to next_field() but takes one character as delimiter */
char *next_token(char **c, char delim)
{
    char *begin = *c;
    if (!*begin) {
        *c = begin;
        return 0;
    }

    char *end = begin;
    while (*end && *end != delim) end++;
    if (*end) {
        *end = 0;
        *c = end + 1;
    }
    else
        *c = end;
    return begin;
}

/* same as next_token() but returns "" instead of 0 if
   no tokens has been found */
char *save_next_token(char **c, char delim)
{
    if (!*c)
        return (char *)"";

    char *result = next_token(c, delim);
    if (result == 0)
        return (char *)"";
    else
        return result;
}


int ends_with(const char *a, const char *b)
{
    return !strcmp(a + strlen(a) - strlen(b), b);
}


