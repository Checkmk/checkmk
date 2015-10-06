// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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


#ifndef STRINGUTIL_H
#define STRINGUTIL_H

#include <vector>
#include <string>
// umm, this is a C header, not actually part of C++ until C++11. This may be a problem in older
// MSVCs
#include <stdint.h>


char *lstrip(char *s);
void rstrip(char *s);
char *strip(char *s);

std::vector<const char*> split_line(char *pos, int (*split_pred)(int));
char *next_word(char **line);

char *llu_to_string(unsigned long long value);
unsigned long long string_to_llu(char *s);

char *ipv4_to_text(uint32_t ip);

void lowercase(char *s);

int parse_boolean(char *value);

// Do a simple pattern matching with the jokers * and ?.
// This is case insensitive (windows-like).
bool globmatch(const char *pattern, const char *astring);

std::string get_last_error_as_string();

#endif // STRINGUTIL_H
