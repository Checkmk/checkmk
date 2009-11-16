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

#ifndef CustomVarsColumn_h
#define CustomVarsColumn_h

#include "Column.h"
#include <string>
#include "nagios.h"

using namespace std;

#define CVT_VARNAMES 0
#define CVT_VALUES   1

class CustomVarsColumn : public Column
{
   int _offset; // within data structure (differs from host/service)
   int _what;

public:
   CustomVarsColumn(string name, string description, int offset, int indirect_offset, int what) 
      : Column(name, description, indirect_offset),  _offset(offset), _what(what) {};
   int type() { return COLTYPE_LIST; };
   void output(void *, Query *);
   Filter *createFilter(int opid, char *value);
   bool contains(void *data, const char *value);
private:
   customvariablesmember *getCVM(void *data);
};


#endif // CustomVarsColumn_h


