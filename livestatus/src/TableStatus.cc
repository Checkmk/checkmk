// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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

#include "TableStatus.h"
#include "global_counters.h"
#include "GlobalCountersColumn.h"
#include "Query.h"

TableStatus::TableStatus()
{
   addColumn(new GlobalCountersColumn("neb_callbacks", 
	    "The number of NEB call backs since program start",           COUNTER_NEB_CALLBACKS,  false));
   addColumn(new GlobalCountersColumn("neb_callbacks_rate", 
	    "The averaged number of NEB call backs per second",           COUNTER_NEB_CALLBACKS,  true));

   addColumn(new GlobalCountersColumn("requests", 
	    "The number of requests to Livestatus since program start",   COUNTER_REQUESTS,       false));
   addColumn(new GlobalCountersColumn("requests_rate", 
	    "The averaged number of request to Livestatus per second",    COUNTER_REQUESTS,       true));

   addColumn(new GlobalCountersColumn("connections", 
	    "The number of client connections to Livestatus since program start",   COUNTER_CONNECTIONS,       false));
   addColumn(new GlobalCountersColumn("connections_rate", 
	    "The averaged number of new client connections to Livestatus per second",    COUNTER_CONNECTIONS,       true));

   addColumn(new GlobalCountersColumn("service_checks", 
	    "The number of completed service checks since program start", COUNTER_SERVICE_CHECKS, false));
   addColumn(new GlobalCountersColumn("service_checks_rate", 
	    "The averaged number of service checks per second",           COUNTER_SERVICE_CHECKS, true));

   addColumn(new GlobalCountersColumn("host_checks", 
	    "The number of host checks since program start",              COUNTER_HOST_CHECKS,    false));
   addColumn(new GlobalCountersColumn("host_checks_rate", 
	    "the averaged number of host checks per second",              COUNTER_HOST_CHECKS,    true));
}

void TableStatus::answerQuery(Query *query)
{
   query->processDataset(0);
}
