// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

#ifndef tables_h
#define tables_h

#ifndef EXTERN
#define EXTERN extern
#endif

class TableContacts;
EXTERN TableContacts      *g_table_contacts;
class TableCommands;
EXTERN TableCommands      *g_table_commands;
class TableHosts;
EXTERN TableHosts         *g_table_hosts;
EXTERN TableHosts         *g_table_hostsbygroup;
class TableServices;
EXTERN TableServices      *g_table_services;
EXTERN TableServices      *g_table_servicesbygroup;
EXTERN TableServices      *g_table_servicesbyhostgroup;
class TableHostgroups;
EXTERN TableHostgroups    *g_table_hostgroups;
class TableServicegroups;
EXTERN TableServicegroups *g_table_servicegroups;
class TableDownComm;
EXTERN TableDownComm      *g_table_downtimes;
EXTERN TableDownComm      *g_table_comments;
class TableTimeperiods;
EXTERN TableTimeperiods   *g_table_timeperiods;
class TableContactgroups;
EXTERN TableContactgroups *g_table_contactgroups;
class TableStatus;
EXTERN TableStatus        *g_table_status;
class TableLog;
EXTERN TableLog           *g_table_log;
class TableColumns;
EXTERN TableColumns       *g_table_columns;

#endif // tables_h

