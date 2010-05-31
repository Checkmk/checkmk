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

#include "TableStatus.h"
#include "global_counters.h"
#include "GlobalCountersColumn.h"
#include "Query.h"
#include "IntPointerColumn.h"
#include "TimePointerColumn.h"
#include "StringPointerColumn.h"
#include "nagios.h"
#include "logger.h"
#include "string.h"

// Nagios status values

extern time_t program_start;
extern int nagios_pid;
extern time_t last_command_check;
extern time_t last_log_rotation;
extern int enable_notifications;
extern int execute_service_checks;
extern int accept_passive_service_checks;
extern int execute_host_checks;
extern int accept_passive_host_checks;
extern int enable_event_handlers;
extern int obsess_over_services;
extern int obsess_over_hosts;
extern int check_service_freshness;
extern int check_host_freshness;
extern int enable_flap_detection;
extern int process_performance_data;
extern int check_external_commands;
extern int num_cached_log_messages;
extern int interval_length;

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

   addColumn(new GlobalCountersColumn("forks", 
	    "The number of process creations since program start",         COUNTER_FORKS,    false));
   addColumn(new GlobalCountersColumn("forks_rate", 
	    "the averaged number of forks checks per second",             COUNTER_FORKS,    true));

   addColumn(new GlobalCountersColumn("log_messages", 
	    "The number of new log messages since program start",         COUNTER_LOG_MESSAGES,    false));
   addColumn(new GlobalCountersColumn("log_messages_rate", 
	    "the averaged number of new log messages per second",         COUNTER_LOG_MESSAGES,    true));

   // Nagios program status data
   addColumn(new IntPointerColumn("nagios_pid", 
	    "The process ID of the Nagios main process", &nagios_pid ));
   addColumn(new IntPointerColumn("enable_notifications", 
	    "Whether notifications are enabled in general (0/1)", &enable_notifications ));
   addColumn(new IntPointerColumn("execute_service_checks", 
	    "Whether active service checks are activated in general (0/1)", &execute_service_checks ));
   addColumn(new IntPointerColumn("accept_passive_service_checks", 
	    "Whether passive service checks are activated in general (0/1)", &accept_passive_service_checks ));
   addColumn(new IntPointerColumn("execute_host_checks", 
	    "Whether host checks are executed in general (0/1)", &execute_host_checks));
   addColumn(new IntPointerColumn("accept_passive_host_checks", 
	    "Whether passive host checks are accepted in general (0/1)", &accept_passive_host_checks));
   addColumn(new IntPointerColumn("enable_event_handlers", 
	    "Whether event handlers are activated in general (0/1)", &enable_event_handlers));
   addColumn(new IntPointerColumn("obsess_over_services", 
	    "Whether Nagios will obsess over service checks and run the ocsp_command (0/1)", &obsess_over_services));
   addColumn(new IntPointerColumn("obsess_over_hosts", 
	    "Whether Nagios will obsess over host checks (0/1)", &obsess_over_hosts));
   addColumn(new IntPointerColumn("check_service_freshness", 
	    "Whether service freshness checking is activated in general (0/1)", &check_service_freshness));
   addColumn(new IntPointerColumn("check_host_freshness", 
	    "Whether host freshness checking is activated in general (0/1)", &check_host_freshness));
   addColumn(new IntPointerColumn("enable_flap_detection", 
	    "Whether flap detection is activated in general (0/1)", &enable_flap_detection));
   addColumn(new IntPointerColumn("process_performance_data", 
	    "Whether processing of performance data is activated in general (0/1)", &process_performance_data));
   addColumn(new IntPointerColumn("check_external_commands", 
	    "Whether Nagios checks for external commands at its command pipe (0/1)", &check_external_commands));
   addColumn(new TimePointerColumn("program_start", 
	    "The time of the last program start as UNIX timestamp", (int*)&program_start));
   addColumn(new TimePointerColumn("last_command_check", 
	    "The time of the last check for a command as UNIX timestamp", (int*)&last_command_check));
   addColumn(new TimePointerColumn("last_log_rotation", 
	    "Time time of the last log file rotation", (int*)&last_log_rotation));
   addColumn(new IntPointerColumn("interval_length", 
	    "The default interval length from nagios.cfg", (int*)&interval_length));

   addColumn(new StringPointerColumn("program_version", 
	    "The version of the monitoring daemon", get_program_version()));
  
   // Livestatus' own status
   addColumn(new IntPointerColumn("cached_log_messages", 
	    "The current number of log messages MK Livestatus keeps in memory", &num_cached_log_messages ));
   addColumn(new StringPointerColumn("livestatus_version",
	    "The version of the MK Livestatus module", (char *)VERSION));
}

void TableStatus::answerQuery(Query *query)
{
   query->processDataset(this);
}
