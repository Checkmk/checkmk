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

#ifndef TableServices_h
#define TableServices_h

#include "config.h"

#include <set>
#include "Table.h"
#include "nagios.h"

using namespace std;
class TableHosts;
class TableContacts;
class TableDowntimes;

class TableServices : public Table
{
    bool _by_group;
    bool _by_hostgroup; // alternative to _by_group

public:
    TableServices(bool by_group, bool by_hostgroup);
    const char *name() { return _by_group ? "servicesbygroup" : \
        (_by_hostgroup ? "servicesbyhostgroup" : "services"); }
    const char *prefixname() { return "services"; }
    bool isAuthorized(contact *, void *);
    void *findObject(char *objectspec);
    void add(service *svc);
    void answerQuery(Query *);
    void addColumns(Table *, string prefix, int indirect_offset, bool add_hosts);
};


#endif // TableServices_h
